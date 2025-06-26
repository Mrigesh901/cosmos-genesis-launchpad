#!/bin/bash

set -e
set -x

# Load dynamic variables
source $(dirname "$0")/env.sh

SCRIPT_DIR=$(pwd)
KEYRING="file"
KEYALGO="eth_secp256k1"

#make install

for (( i=1; i<=${NUM_NODES}; i++ )); do
  rm -rf "$SCRIPT_DIR/${MONIKER_PREFIX}${i}"
done

FIRST_NODE_HOME="$SCRIPT_DIR/${MONIKER_PREFIX}1"
cronosd init "${MONIKER_PREFIX}1" --chain-id $CHAINID --home "$FIRST_NODE_HOME"
cp "$SCRIPT_DIR/generated_genesis.json" "$FIRST_NODE_HOME/config/genesis.json"

VAL_KEY_NAME="${KEY}1"
VAL_PASSWORD=${KEYRING_PASSWORDS[0]}

KEY_OUTPUT=$(echo -e "${VAL_PASSWORD}\n${VAL_PASSWORD}" | cronosd keys add "$VAL_KEY_NAME" --keyring-backend $KEYRING --algo $KEYALGO --home "$FIRST_NODE_HOME" --output json)
echo "$KEY_OUTPUT" > "$SCRIPT_DIR/${MONIKER_PREFIX}1/key_info.json"

VAL_ADDRESS=$(echo -e "${VAL_PASSWORD}" | cronosd keys show "$VAL_KEY_NAME" -a --keyring-backend $KEYRING --home "$FIRST_NODE_HOME")

# cronosd genesis add-genesis-account "$VAL_ADDRESS" 10500000000000000000000000aauth --home "$FIRST_NODE_HOME"
cronosd genesis add-genesis-account "$VAL_ADDRESS" "$VALIDATOR_STAKE" --home "$FIRST_NODE_HOME"

echo "Validator 1 address: $VAL_ADDRESS"

setupNode() {
  NODE_NUM=$1
  MONIKER="${MONIKER_PREFIX}${NODE_NUM}"
  HOMEDIR="$SCRIPT_DIR/${MONIKER}"
  VAL_KEY_NAME="${KEY}${NODE_NUM}"
  VAL_PASSWORD=${KEYRING_PASSWORDS[$((NODE_NUM-1))]}

  cronosd init "$MONIKER" --chain-id $CHAINID --home "$HOMEDIR"
  cp "$FIRST_NODE_HOME/config/genesis.json" "$HOMEDIR/config/genesis.json"

  KEY_OUTPUT=$(echo -e "${VAL_PASSWORD}\n${VAL_PASSWORD}" | cronosd keys add "$VAL_KEY_NAME" --keyring-backend $KEYRING --algo $KEYALGO --home "$HOMEDIR" --output json)
  echo "$KEY_OUTPUT" > "$HOMEDIR/key_info.json"

  VAL_ADDRESS=$(echo -e "${VAL_PASSWORD}" | cronosd keys show "$VAL_KEY_NAME" -a --keyring-backend $KEYRING --home "$HOMEDIR")

  cronosd genesis add-genesis-account "$VAL_ADDRESS" 10500000000000000000000000aauth --home "$FIRST_NODE_HOME"
  cronosd genesis add-genesis-account "$VAL_ADDRESS" 10500000000000000000000000aauth --home "$HOMEDIR"

  echo "Validator $NODE_NUM address: $VAL_ADDRESS"
}

for (( i=2; i<=${NUM_NODES}; i++ )); do
  setupNode $i
done

VAL_KEY_NAME="${KEY}1"
VAL_PASSWORD=${KEYRING_PASSWORDS[0]}

echo -e "${VAL_PASSWORD}" | cronosd genesis gentx "$VAL_KEY_NAME" 1000000000000000000aauth --keyring-backend $KEYRING --home "$FIRST_NODE_HOME" --chain-id $CHAINID --ip "${VALIDATOR_IPS[0]}" -y

for (( i=2; i<=${NUM_NODES}; i++ )); do
  NODE_NUM=$i
  HOMEDIR="$SCRIPT_DIR/${MONIKER_PREFIX}${NODE_NUM}"
  VAL_KEY_NAME="${KEY}${NODE_NUM}"
  VAL_PASSWORD=${KEYRING_PASSWORDS[$((NODE_NUM-1))]}

  echo -e "${VAL_PASSWORD}" | cronosd genesis gentx "$VAL_KEY_NAME" 1000000000000000000aauth --keyring-backend $KEYRING --home "$HOMEDIR" --chain-id $CHAINID --ip "${VALIDATOR_IPS[$NODE_NUM-1]}" -y
done

GENTX_DIR="$FIRST_NODE_HOME/config/gentx"
mkdir -p "$GENTX_DIR"
for (( i=2; i<=${NUM_NODES}; i++ )); do
  GENTX_SRC_DIR="$SCRIPT_DIR/${MONIKER_PREFIX}${i}/config/gentx"
  if [ -d "$GENTX_SRC_DIR" ]; then
    cp "$GENTX_SRC_DIR/"*.json "$GENTX_DIR/"
  fi
done

cronosd genesis collect-gentxs --home "$FIRST_NODE_HOME"
cronosd genesis validate --home "$FIRST_NODE_HOME"

for (( i=1; i<=${NUM_NODES}; i++ )); do
  NODE_HOME="$SCRIPT_DIR/${MONIKER_PREFIX}${i}"
  if [ "$FIRST_NODE_HOME" != "$NODE_HOME" ]; then
    cp "$FIRST_NODE_HOME/config/genesis.json" "$NODE_HOME/config/genesis.json"
  fi
done

echo "Node configurations generated using '$KEYRING' keyring backend. You can now copy each node's directory to the respective system."

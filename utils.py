import json
import subprocess

def load_genesis():
    with open('template_genesis.json') as f:
        return json.load(f)

def save_genesis(genesis):
    with open('generated_genesis.json', 'w') as f:
        json.dump(genesis, f, indent=2)

def update_genesis(inflation_rate_change, inflation_max, inflation_min, goal_bonded, blocks_per_year,
                   mint_denom, voting_period, max_deposit_period, max_validators, max_gas, time_iota_ms):
    
    genesis = load_genesis()

    # Update mint parameters
    mint_params = genesis["app_state"]["mint"]["params"]
    mint_params["inflation_rate_change"] = str(inflation_rate_change)
    mint_params["inflation_max"] = str(inflation_max)
    mint_params["inflation_min"] = str(inflation_min)
    mint_params["goal_bonded"] = str(goal_bonded)
    mint_params["blocks_per_year"] = str(blocks_per_year)
    mint_params["mint_denom"] = mint_denom

    # Apply mint_denom globally
    staking_params = genesis["app_state"]["staking"]["params"]
    staking_params["bond_denom"] = mint_denom
    staking_params["max_validators"] = max_validators

    crisis_params = genesis["app_state"]["crisis"]["constant_fee"]
    crisis_params["denom"] = mint_denom

    gov_params = genesis["app_state"]["gov"]["params"]
    gov_params["voting_period"] = voting_period
    gov_params["max_deposit_period"] = max_deposit_period

    if gov_params.get("min_deposit") and len(gov_params["min_deposit"]) > 0:
        gov_params["min_deposit"][0]["denom"] = mint_denom

    if gov_params.get("expedited_min_deposit") and len(gov_params["expedited_min_deposit"]) > 0:
        gov_params["expedited_min_deposit"][0]["denom"] = mint_denom

    # Apply evm denom (create if missing)
    evm_params = genesis["app_state"].setdefault("evm", {}).setdefault("params", {})
    evm_params["evm_denom"] = mint_denom

    # Ensure chain_config is fully initialized
    evm_params["chain_config"] = {
        "homestead_block": "0x0",
        "dao_fork_block": "0x0",
        "dao_fork_support": True,
        "eip150_block": "0x0",
        "eip150_hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "eip155_block": "0x0",
        "eip158_block": "0x0",
        "byzantium_block": "0x0",
        "constantinople_block": "0x0",
        "petersburg_block": "0x0",
        "istanbul_block": "0x0",
        "muir_glacier_block": "0x0",
        "berlin_block": "0x0",
        "london_block": "0x0",
        "arrow_glacier_block": "0x0",
        "gray_glacier_block": "0x0"
    }

    # Update Governance Parameters
    genesis["app_state"]["gov"]["voting_params"] = {"voting_period": voting_period}
    genesis["app_state"]["gov"]["deposit_params"] = {"max_deposit_period": max_deposit_period}

    # Update Consensus Parameters
    consensus_params = genesis["consensus"]["params"]["block"]
    consensus_params["max_gas"] = str(max_gas)
    consensus_params["time_iota_ms"] = str(time_iota_ms)

    # Save the updated genesis
    save_genesis(genesis)

    return genesis


def write_env_file(num_nodes, chain_id, key_name, moniker_prefix, validator_ips, keyring_passwords):
    ip_string = " ".join(validator_ips)
    password_string = " ".join(keyring_passwords)

    env_content = f"""NUM_NODES={num_nodes}
CHAINID={chain_id}
KEY={key_name}
MONIKER_PREFIX={moniker_prefix}
KEYRING_PASSWORDS=({password_string})
VALIDATOR_IPS=({ip_string})
"""

    with open("scripts/env.sh", "w") as f:
        f.write(env_content)

def run_init_script(num_nodes, chain_id, key_name, moniker_prefix, validator_ips, keyring_passwords):
    write_env_file(num_nodes, chain_id, key_name, moniker_prefix, validator_ips, keyring_passwords)

    try:
        result = subprocess.run(["bash", "scripts/init.sh"], capture_output=True, text=True)
        return result.stdout + "\n" + result.stderr
    except Exception as e:
        return str(e)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math
from simulate import simulate_tokenomics
from utils import update_genesis, save_genesis, run_init_script
import streamlit.components.v1 as components # Import components for custom HTML


st.set_page_config(page_title="Cosmos Tokenomics Dashboard", layout="wide")

# Custom CSS for better aesthetics (example - you can expand this)
st.markdown("""
<style>
    .stApp {
        color: 3fa306;
    }
    .stSidebar {
        
        border-right: 1px solid #e0e0e0;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1.1em;
        padding: 10px 15px;
        border-radius: 8px 8px 0 0;
        margin: 0 5px;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #4CAF50; /* Green for selected tab */
        color: white;
        font-weight: bold;
    }
    .stMetric {
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50; /* Darker headings */
    }
    .stTooltip {
        background-color: #e0f7fa !important;  /* light blue */
        color: white !important;
        padding: 5px;
        border-radius: 5px;
        font-size: 0.9em;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def load_env(filepath="scripts/env.sh"):
    env_vars = {}
    with open(filepath, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                value = value.strip().strip('"')
                # Remove surrounding () from arrays like (a b c)
                if value.startswith("(") and value.endswith(")"):
                    value = value[1:-1].strip().split()
                env_vars[key] = value
    return env_vars

env = load_env()

# Constants
AVERAGE_TX_GAS_COST = 20000  # average gas per simple transaction
TOKEN_DECIMALS = 18
# INITIAL_VALIDATOR_TOKEN_RAW = 31500000000000000000000000  # Example: 31 million tokens per validator (raw)
GENTX_STAKE_RAW = 1000000000000000000000000  # Example: 10 million tokens per gentx stake

st.title("Cosmos Chain Tokenomics Dashboard")

# Sidebar: Chain Parameters

# Mint Parameters
st.sidebar.header("⚙️ Chain Parameters")
#num_nodes = st.sidebar.number_input("Number of Validator Nodes", min_value=1, value=3, step=1)
num_nodes = st.sidebar.slider(
    "Number of Validator Nodes",
    min_value=1,
    max_value=5,
    value=3,
    step=1,
    help="The total validators at genesis"
)
NUM_VALIDATORS_AT_GENESIS = num_nodes
initial_tokens_per_validator = st.sidebar.number_input(
    "Initial Token Allocation per Validator (Whole Tokens)",
    min_value=1,
    value=10_500_000,  # Default to 10 million
    step=100,
    help="The initial allocation of tokens defines the starting total supply and how wealth/staking power is distributed among genesis accounts."
)
INITIAL_VALIDATOR_TOKEN_RAW = initial_tokens_per_validator * 10**18

st.sidebar.header("Mint Parameters")
inflation_rate_change = st.sidebar.number_input("Inflation Rate Change", min_value=0.0, max_value=1.0, value=0.13, step=0.01, format="%.8f")
inflation_max = st.sidebar.number_input("Inflation Max", min_value=0.0, max_value=1.0, value=0.20, step=0.01, format="%.8f")
inflation_min = st.sidebar.number_input("Inflation Min", min_value=0.0, max_value=1.0, value=0.07, step=0.01, format="%.8f")
goal_bonded = st.sidebar.number_input("Goal Bonded", min_value=0.0, max_value=1.0, value=0.67, step=0.01, format="%.8f", help="percentage of tokens staked/locked at genesis")
blocks_per_year = st.sidebar.number_input("Blocks Per Year", min_value=1, value=6311520)
mint_denom = st.sidebar.text_input("Mint Denomination", value="aauth")

max_supply_tokens = st.sidebar.number_input("Max Supply (in whole units)", min_value=1, value=1_000_000_000, step=1, format="%d")
max_supply = max_supply_tokens * 10 ** 18  # Atto units

# Governance Parameters
st.sidebar.header("Governance Parameters")
voting_period = st.sidebar.text_input("Voting Period", value="600s", help="The duration for which a governance proposal is open for voting.")
expedited_voting_period = st.sidebar.text_input("Expidited voting period (must be less than voting period)", value="300s")
max_deposit_period = st.sidebar.text_input("Max Deposit Period", value="600s", help="The maximum time allowed for a proposal to gather the minimum required deposit to enter the voting period.")

# Staking Parameters
st.sidebar.header("Staking Parameters")
max_validators = st.sidebar.number_input("Max Validators", min_value=1, value=100, help="the initial decentralization limit. As more participants join and stake tokens, the network can become more decentralized, up to this configured limit.")
max_gas = st.sidebar.number_input("Max Gas", min_value=1, value=30_000_000, help="defines the chain's scalability limit at genesis. It's a balance between allowing high transaction throughput and preventing block processing from becoming too computationally intensive for validators.")
time_iota_ms = st.sidebar.number_input("Time Iota (ms)", min_value=1, value=6000, help="A shorter `time_iota_ms` means faster transaction finality but generally results in higher network overhead and potentially more resource demanding validators.")
min_deposit = st.sidebar.number_input("Min Deposit (tokens)", min_value=1.0, value=10000000.0, help="The minimum amount of tokens required for a proposal to be considered valid and enter the voting period. This acts as a spam filter.")


def parse_duration(duration_str):
    """
    Parses a duration string like '172800s' into seconds as an integer.
    """
    if duration_str.endswith('s'):
        return int(duration_str[:-1])
    else:
        return int(duration_str)

voting_period_seconds = parse_duration(voting_period)
max_deposit_period_seconds = parse_duration(max_deposit_period)


tab1, tab2 = st.tabs(["📝 Chain Design & Predictions", "📈 Tokenomics Simulation"])

# ======== Tab 1: Chain Design & Predictions ========

with tab1:
    st.header("⛓️ Chain Design & Genesis Predictions")

    col1, col2, col3 = st.columns(3)
    with col1:
        time_iota_seconds = time_iota_ms/1000
        st.metric("Target Block Time (s)", f"{time_iota_ms / 1000:.2f}")
        
    with col2:
        predicted_bps = 1000 / time_iota_ms
        st.metric("Predicted Blocks Per Second", f"{predicted_bps:.2f} bps")
        
    with col3:
        predicted_tps = (max_gas / AVERAGE_TX_GAS_COST) / (time_iota_ms / 1000)
        st.metric("Predicted Max TPS", f"{predicted_tps:.2f} tx/s")

    st.subheader("📈 Predicted Cumulative Blocks Over 24 Hours")
    time_hours = list(range(0, 25))
    cumulative_blocks = [(hour * 3600) * predicted_bps for hour in time_hours]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_hours, y=cumulative_blocks, mode='lines+markers', name='Cumulative Blocks'))
    fig.update_layout(xaxis_title='Hours', yaxis_title='Blocks', title='Cumulative Blocks Prediction')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧱 Block Capacity Visualization")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Max Gas"], y=[max_gas], name='Max Gas Per Block'))
    fig.add_trace(go.Bar(x=["Estimated Gas For Tx"], y=[AVERAGE_TX_GAS_COST], name='Avg. Tx Gas Cost'))
    fig.update_layout(barmode='group', title='Block Gas Capacity')
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown(
        f"""
        <small><code>max_gas</code>: The maximum total gas that can be consumed by all transactions in a single block.
        This acts as a soft block size limit and is a primary factor for the chain's transaction throughput capacity.</small>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        f"""
        <small>
        **Narrative:** `max_gas` represents the chain's fundamental "scalability limit" at genesis.
        A higher `max_gas` allows for more transactions per block,but also requires more processing power from validators.
        </small>
        """,
        unsafe_allow_html=True
    )

    st.subheader("🔐 Decentralization and Validator Set")
    st.metric("Maximum Active Validators", f"{max_validators}")
    decentralization_ratio = NUM_VALIDATORS_AT_GENESIS / max_validators
    st.progress(decentralization_ratio)

    st.subheader("💰 Initial Token Allocation")
    total_initial_supply = NUM_VALIDATORS_AT_GENESIS * INITIAL_VALIDATOR_TOKEN_RAW
    st.metric("Total Initial Supply", f"{total_initial_supply / 1e18:.2f} tokens")
    st.metric("Genesis Transaction Stake", f"{GENTX_STAKE_RAW / 1e18:.2f} tokens")

    fig = go.Figure(data=[go.Pie(labels=[f"Validator {i+1}" for i in range(NUM_VALIDATORS_AT_GENESIS)],
                                 values=[INITIAL_VALIDATOR_TOKEN_RAW for _ in range(NUM_VALIDATORS_AT_GENESIS)])])
    fig.update_layout(title='Initial Token Distribution')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🗳️ Governance Settings")
    st.write(f"Voting Period: {voting_period_seconds / 60:.0f} minutes")
    st.write(f"Max Deposit Period: {max_deposit_period_seconds / 60:.0f} minutes")
    st.write(f"Minimum Deposit: {min_deposit} {mint_denom}")


# ======== Tab 2: Tokenomics Simulation ========
with tab2:
    st.header("📈 Tokenomics Simulation")

    try:
        inflation_series, supply_series, provision_series, staking_apr_series = simulate_tokenomics(
            inflation_rate_change, inflation_max, inflation_min,
            goal_bonded, blocks_per_year, max_supply
        )

        st.subheader("💰 Current Supply Distribution")
        staked_tokens = max_supply * goal_bonded
        non_bonded_tokens = max_supply - staked_tokens

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Supply", f"{max_supply / 1e18:.2f} tokens")
            st.metric("Staked Tokens", f"{staked_tokens / 1e18:.2f} tokens")
            st.metric("Bonded Ratio", f"{goal_bonded:.2%}")
            st.metric("Non-Bonded Tokens", f"{non_bonded_tokens / 1e18:.2f} tokens")

        with col2:
            fig = go.Figure(data=[go.Pie(labels=['Staked', 'Non-Staked'], values=[staked_tokens, non_bonded_tokens])])
            fig.update_layout(title='Current Supply Distribution')
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📈 Inflation & Rewards Over Time")
        years = list(range(1, 11))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=inflation_series, mode='lines+markers', name='Inflation %'))
        fig.add_trace(go.Scatter(x=years, y=provision_series, mode='lines+markers', name='Rewards per Block'))
        fig.update_layout(title='Inflation and Rewards Over Years', xaxis_title='Year')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📈 Predicted Staking APR Over Years")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=staking_apr_series, mode='lines+markers', name='Staking APR'))
        fig.update_layout(title='Staking APR Prediction', xaxis_title='Year')
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("⛓️ Block Production Stats")
        bps = float(blocks_per_year) / (365 * 24 * 3600)
        st.metric("Blocks Per Second", f"{bps:.2f} bps")
        st.metric("Blocks Per Year", f"{blocks_per_year:.0f} blocks")

        minted_per_second = provision_series[-1] * float(blocks_per_year) / (365 * 24 * 3600)
        st.metric("Tokens Minted Per Second", f"{minted_per_second:.6f} tokens/sec (in atto untis)")

        fig = go.Figure(data=[go.Pie(labels=['Rewards (per block)', 'Inflation %'],
                                     values=[provision_series[-1], inflation_series[-1]])])
        fig.update_layout(title='Rewards vs Inflation Distribution (Last Year)')
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Simulation Error: {e}")


################################################################################
################################################################################


# Genesis File Generation
st.markdown("---")
st.subheader("Generate Genesis File")
if st.button("Generate Genesis JSON"):
    try:
        updated_genesis = update_genesis(
            inflation_rate_change, inflation_max, inflation_min, goal_bonded, blocks_per_year,
            mint_denom, voting_period, expedited_voting_period, max_deposit_period, max_validators, max_gas, time_iota_ms
        )
        save_genesis(updated_genesis)
        st.success("Genesis file generated successfully as generated_genesis.json")
    except Exception as e:
        st.error(f"Error generating genesis file: {e}")

# Node Initialization
st.markdown("---")
st.subheader("Run Node Initialization Script")
num_nodes = st.number_input("Number of Nodes", min_value=1, value=num_nodes)
chain_id = st.text_input("Chain ID", value="cronostestnet_338-3")
key_name = st.text_input("Key Name", value="key")
moniker_prefix = st.text_input("Moniker Prefix", value="cronos-node")

validator_ips = []
keyring_passwords = []

for i in range(num_nodes):
    st.markdown(f"#### Validator {i + 1} Config")
    validator_ips.append(st.text_input(f"Validator {i + 1} IP", key=f"ip_{i}"))
    keyring_passwords.append(st.text_input(f"Validator {i + 1} Keyring Password", key=f"pw_{i}", type="password"))

if st.button("Run Initialization Script"):
    try:
        init_output = run_init_script(num_nodes, chain_id, key_name, moniker_prefix, validator_ips, keyring_passwords, INITIAL_VALIDATOR_TOKEN_RAW, mint_denom)
        st.text_area("Initialization Output", init_output, height=300)
    except Exception as e:
        st.error(f"Error running initialization script: {e}")

st.markdown("---")
st.info("Designed for Cosmos SDK chains with real-time tokenomics visualization and chain bootstrapping.")
st.info("Made by Mrigesh with ❤ .  @copyright mrigesh.patni 2025")
import streamlit as st
import plotly.graph_objects as go
from simulate import simulate_tokenomics
from utils import update_genesis, save_genesis, run_init_script

# Page configuration
st.set_page_config(
    page_title="Cosmos Tokenomics Configurator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
st.sidebar.title("⚙️ Tokenomics Configurator")
st.sidebar.markdown("Customize your Cosmos SDK chain parameters below.")

# Main Dashboard Header
st.title("🚀 Cosmos Chain Tokenomics Dashboard")
st.markdown("### Visualize and Configure Your Chain Parameters in Real-Time")

# Layout Columns
col1, col2, col3 = st.columns([1, 1, 1])

# Mint Parameters Input
with col1:
    st.subheader("Mint Parameters")
    inflation_rate_change = st.number_input("Inflation Rate Change", min_value=0.0, max_value=1.0, value=0.13, step=0.01, format="%.8f")
    inflation_max = st.number_input("Inflation Max", min_value=0.0, max_value=1.0, value=0.20, step=0.01, format="%.8f")
    inflation_min = st.number_input("Inflation Min", min_value=0.0, max_value=1.0, value=0.07, step=0.01, format="%.8f")
    goal_bonded = st.number_input("Goal Bonded", min_value=0.0, max_value=1.0, value=0.67, step=0.01, format="%.8f")
    blocks_per_year = st.number_input("Blocks Per Year", min_value=1, value=6311520)
    mint_denom = st.text_input("Mint Denomination", value="aauth")
    
    max_supply_tokens = st.number_input(
        "Max Supply (whole tokens)",  
        min_value=1,  # Prevent zero or negative supply
        value=1_000_000_000,  # Default 1 billion tokens
        step=1,
        format="%d"
    )
    max_supply = max_supply_tokens * 10 ** 18  # Convert to atto units

# Governance Parameters Input
with col2:
    st.subheader("Governance Parameters")
    voting_period = st.text_input("Voting Period", value="600s")
    max_deposit_period = st.text_input("Max Deposit Period", value="600s")

# Staking and Consensus Parameters Input
with col3:
    st.subheader("Staking & Consensus Parameters")
    max_validators = st.number_input("Max Validators", min_value=1, value=100)
    max_gas = st.number_input("Max Gas", min_value=1, value=30_000_000)
    time_iota_ms = st.number_input("Time Iota (ms)", min_value=1, value=6000)

# Simulation Execution
try:
    results = simulate_tokenomics(
        inflation_rate_change, inflation_max, inflation_min,
        goal_bonded, blocks_per_year, max_supply
    )

    inflation_series, supply_series, provision_series, staking_apr_series = results

    # Live Charts
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=inflation_series, mode='lines', name='Inflation %'))
        fig.update_layout(title='Inflation Over Time', xaxis_title='Years', yaxis_title='Inflation %')
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=supply_series, mode='lines', name='Total Supply'))
        fig.update_layout(title='Total Supply Over Time', xaxis_title='Years', yaxis_title='Supply')
        st.plotly_chart(fig, use_container_width=True)

    chart_col3, chart_col4 = st.columns(2)
    with chart_col3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=provision_series, mode='lines', name='Block Provision'))
        fig.update_layout(title='Provision Per Block Over Time', xaxis_title='Years', yaxis_title='Provision Per Block')
        st.plotly_chart(fig, use_container_width=True)

    with chart_col4:
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=staking_apr_series, mode='lines', name='Staking APR'))
        fig.update_layout(title='Staking APR Over Time', xaxis_title='Years', yaxis_title='Staking APR %')
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Error in simulation: {e}")

# Genesis File Generation
st.markdown("---")
st.subheader("Generate Genesis File")
if st.button("Generate Genesis JSON"):
    try:
        updated_genesis = update_genesis(
            inflation_rate_change, inflation_max, inflation_min, goal_bonded, blocks_per_year,
            mint_denom, voting_period, max_deposit_period, max_validators, max_gas, time_iota_ms
        )
        save_genesis(updated_genesis)
        st.success("Genesis file generated successfully as generated_genesis.json")
    except Exception as e:
        st.error(f"Error generating genesis file: {e}")

# Node Initialization Section
st.markdown("---")
st.subheader("Run Node Initialization Script")
num_nodes = st.number_input("Number of Nodes", min_value=1, value=3)
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
        init_output = run_init_script(num_nodes, chain_id, key_name, moniker_prefix, validator_ips, keyring_passwords)
        st.text_area("Initialization Output", init_output, height=300)
    except Exception as e:
        st.error(f"Error running initialization script: {e}")

st.markdown("---")
st.info("Designed for Cosmos SDK chains with real-time tokenomics visualization and chain bootstrapping.")

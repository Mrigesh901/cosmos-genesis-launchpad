from decimal import Decimal, getcontext

getcontext().prec = 18

def simulate_tokenomics(inflation_rate_change, inflation_max, inflation_min, goal_bonded, blocks_per_year, max_supply, years=10):
    # Ensure all inputs are Decimals
    inflation_rate_change = Decimal(str(inflation_rate_change))
    inflation_max = Decimal(str(inflation_max))
    inflation_min = Decimal(str(inflation_min))
    goal_bonded = Decimal(str(goal_bonded))
    blocks_per_year = Decimal(str(blocks_per_year))
    max_supply = Decimal(str(max_supply))

    inflation = inflation_max
    bonded_ratio = goal_bonded
    total_supply = max_supply
    provision_per_block = Decimal(0)
    staking_apr = Decimal(0.0)

    inflation_values = []
    supply_values = []
    provision_values = []
    apr_values = []

    for year in range(1, years + 1):
        inflation = min(inflation * (Decimal('1') - inflation_rate_change), inflation_min)
        annual_provisions = inflation * total_supply
        provision_per_block = annual_provisions / blocks_per_year
        total_supply += annual_provisions
        staking_apr = inflation / bonded_ratio if bonded_ratio > 0 else Decimal('0')

        inflation_values.append(float(inflation))
        supply_values.append(float(total_supply))
        provision_values.append(float(provision_per_block))
        apr_values.append(float(staking_apr))

    return inflation_values, supply_values, provision_values, apr_values

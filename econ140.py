import pandas as pd
import zipfile
import io          # lets us wrap the bytes stream as text for pandas
import os
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib.gridspec as gridspec
from statsmodels.tsa.seasonal import seasonal_decompose

# Parameters for the analysis
zip_files = [f"{year}_qtrly_by_area.zip" for year in range(2013, 2018)]
area_codes = ["06000", "48000"]  # California and Texas
area_names = {"06000": "California", "48000": "Texas"}
start_year = 2013
end_year = 2017
policy_implementation = (2015, 3)  # 2015 Q3

# Industry codes for analysis
target_industry_code = 722511  # Full-service restaurants
control_industry_code = 722513  # Limited-service restaurants (for triple diff)

print(f"Processing zip files: {zip_files}")

# Function to extract restaurant data from a zip file
def extract_restaurant_data(zip_file, state_codes):
    """Extract restaurant data for specified states and industries"""
    all_data = []
    
    try:
        with zipfile.ZipFile(zip_file) as z:
            # Identify the year from the zip filename
            year = int(zip_file.split('_')[0])
            
            # For each state, find the statewide file
            for state_code in state_codes:
                # Pattern for the statewide file
                state_pattern = f"{state_code} "
                
                # Find files for this state
                potential_files = [f for f in z.namelist() if state_pattern in f and f.endswith('.csv')]
                
                if not potential_files:
                    print(f"No state files found for {state_code} in {zip_file}")
                    continue
                
                # Process each potential file
                for file_path in potential_files:
                    print(f"Processing {file_path} from {zip_file}")
                    
                    with z.open(file_path) as raw_bytes, \
                         io.TextIOWrapper(raw_bytes, encoding="utf-8") as text_file:
                        
                        # Read the CSV
                        df = pd.read_csv(text_file)
                        
                        # Look for restaurant data using both code and text methods
                        restaurant_df = df[
                            (df['industry_code'] == target_industry_code) | 
                            (df['industry_code'] == control_industry_code) |
                            (df['industry_title'].str.contains('Full-Service Restaurant', case=False, na=False)) |
                            (df['industry_title'].str.contains('Limited-Service Restaurant', case=False, na=False))
                        ]
                        
                        # If no records found, look for any restaurant records (industry_code starting with 722)
                        if restaurant_df.empty:
                            restaurant_df = df[
                                (df['industry_code'] >= 722000) & (df['industry_code'] < 723000) |
                                (df['industry_title'].str.contains('Restaurant', case=False, na=False))
                            ]
                        
                        if not restaurant_df.empty:
                            print(f"Found {len(restaurant_df)} restaurant records in {file_path}")
                            
                            # Add a column to indicate target vs control industry
                            # Target = full service, Control = limited service
                            def determine_industry_type(row):
                                if row['industry_code'] == target_industry_code or 'Full-Service' in str(row['industry_title']):
                                    return 1  # Target (Full-service)
                                elif row['industry_code'] == control_industry_code or 'Limited-Service' in str(row['industry_title']):
                                    return 0  # Control (Limited-service)
                                else:
                                    # For other restaurant types, classify based on description
                                    if 'Full' in str(row['industry_title']):
                                        return 1
                                    else:
                                        return 0
                                    
                            restaurant_df['target_industry'] = restaurant_df.apply(determine_industry_type, axis=1)
                            
                            # Print the distribution of industry types
                            print("Industry distribution:")
                            print(restaurant_df.groupby(['industry_code', 'industry_title', 'target_industry']).size())
                            
                            # Ensure we have year and quarter columns
                            # Extract quarter from file path if possible
                            if 'year' not in restaurant_df.columns:
                                restaurant_df['year'] = year
                            
                            # If 'qtr' isn't in the data, try to extract it from the file name or
                            # assign quarters to groups of 3 months
                            if 'qtr' not in restaurant_df.columns:
                                # Try to find quarter info in the filename
                                # Since we have data for all quarters in one file, assign each row a quarter
                                if len(restaurant_df) == 4:  # One record per quarter
                                    restaurant_df['qtr'] = [1, 2, 3, 4]
                                elif len(restaurant_df) % 4 == 0:  # Multiple records per quarter
                                    records_per_qtr = len(restaurant_df) // 4
                                    qtrs = []
                                    for q in range(1, 5):
                                        qtrs.extend([q] * records_per_qtr)
                                    restaurant_df['qtr'] = qtrs
                                else:
                                    # If can't determine, use month columns if available
                                    if all(col in restaurant_df.columns for col in ['month1_emplvl', 'month2_emplvl', 'month3_emplvl']):
                                        restaurant_df['qtr'] = 1  # Default to Q1 if can't determine
                            
                            all_data.append(restaurant_df)
                        else:
                            print(f"No restaurant data found in {file_path}")
    
    except Exception as e:
        print(f"Error processing {zip_file}: {str(e)}")
    
    # Combine all results from this zip file
    if all_data:
        result_df = pd.concat(all_data, ignore_index=True)
        print(f"Total records extracted from {zip_file}: {len(result_df)}")
        return result_df
    else:
        print(f"No restaurant data found in {zip_file}")
        return pd.DataFrame()

# Collect data from all zip files
print("\nExtracting restaurant data from all zip files...")
all_restaurant_data = []

for zip_file in zip_files:
    if os.path.exists(zip_file):
        print(f"\nProcessing {zip_file}...")
        year_data = extract_restaurant_data(zip_file, area_codes)
        
        if not year_data.empty:
            # Add year to the data
            data_year = int(zip_file.split('_')[0])
            if 'year' not in year_data.columns:
                year_data['year'] = data_year
            year_data['data_year'] = data_year
            
            # If we don't have quarter info, try to infer it
            if 'qtr' not in year_data.columns:
                # For quarterly data, try to assign quarters based on position
                n_records_per_state_industry = year_data.groupby(['area_fips', 'industry_code']).size().max()
                if n_records_per_state_industry == 4:
                    # If we have 4 records per state/industry, assume they're quarters
                    # First sort by state, industry, then some employment metric
                    sort_col = 'month1_emplvl' if 'month1_emplvl' in year_data.columns else 'avg_wkly_wage'
                    year_data = year_data.sort_values(['area_fips', 'industry_code', sort_col])
                    
                    # Group by state and industry and assign quarters
                    def assign_quarters(group):
                        group['qtr'] = list(range(1, len(group) + 1))
                        return group
                    
                    year_data = year_data.groupby(['area_fips', 'industry_code'], group_keys=False).apply(assign_quarters)
                else:
                    # Default to one quarter per year if can't determine
                    year_data['qtr'] = 1
                
            all_restaurant_data.append(year_data)
        else:
            print(f"No data found in {zip_file}")
    else:
        print(f"Warning: {zip_file} not found")

# Combine all the data
if all_restaurant_data:
    restaurant_df = pd.concat(all_restaurant_data, ignore_index=True)
    print(f"\nTotal records in combined dataset: {len(restaurant_df)}")
    
    # Display the unique industry codes and titles
    print("\nUnique industry codes and titles in the dataset:")
    industry_summary = restaurant_df.groupby(['industry_code', 'industry_title']).size().reset_index(name='count')
    print(industry_summary.sort_values('count', ascending=False))
    
    # Make sure we have the required columns
    if 'qtr' not in restaurant_df.columns:
        print("Warning: 'qtr' column not found. Creating a default quarterly column.")
        restaurant_df['qtr'] = 1  # Default value
else:
    print("No data found in any of the zip files")
    exit()

# Process and analyze the data
print("\nPreparing data for analysis...")

# Display column information
print("\nColumns in the dataset:")
print(restaurant_df.columns.tolist())

# Select and rename relevant columns
columns_to_keep = [
    'area_fips', 'area_title', 'industry_code', 'industry_title', 
    'year', 'qtr', 'month1_emplvl', 'month2_emplvl', 'month3_emplvl',
    'total_qtrly_wages', 'avg_wkly_wage', 'target_industry', 'data_year'
]

# Keep only the columns that exist in the dataset
columns_to_keep = [col for col in columns_to_keep if col in restaurant_df.columns]
restaurant_data = restaurant_df[columns_to_keep].copy()

# Check the unique values in area_fips and industry_code
print("\nUnique area_fips values:")
print(restaurant_data['area_fips'].unique())
print("\nUnique industry_code values:")
print(restaurant_data['industry_code'].unique())
print("\nUnique year and quarter combinations:")
print(restaurant_data.groupby(['year', 'qtr']).size().reset_index())

# Calculate quarterly average employment
if all(col in restaurant_data.columns for col in ['month1_emplvl', 'month2_emplvl', 'month3_emplvl']):
    restaurant_data['avg_emplvl'] = restaurant_data[['month1_emplvl', 'month2_emplvl', 'month3_emplvl']].mean(axis=1)
else:
    # If we don't have monthly data, use another measure if available
    if 'total_qtrly_wages' in restaurant_data.columns and 'avg_wkly_wage' in restaurant_data.columns:
        # Can estimate employment from wages
        restaurant_data['avg_emplvl'] = restaurant_data['total_qtrly_wages'] / (restaurant_data['avg_wkly_wage'] * 13)
    else:
        print("Warning: Cannot calculate average employment - missing required columns.")
        restaurant_data['avg_emplvl'] = 0  # Default value

# Calculate employment size categories for heterogeneity analysis
try:
    employment_quantiles = restaurant_data.groupby('industry_code')['avg_emplvl'].quantile([0.33, 0.67]).unstack()

    def size_category(row):
        industry = row['industry_code']
        emp_level = row['avg_emplvl']
        if industry in employment_quantiles.index:
            if emp_level <= employment_quantiles.loc[industry, 0.33]:
                return 'small'
            elif emp_level <= employment_quantiles.loc[industry, 0.67]:
                return 'medium'
            else:
                return 'large'
        return 'unknown'

    restaurant_data['size_category'] = restaurant_data.apply(size_category, axis=1)
    print("\nDistribution of restaurant size categories:")
    print(restaurant_data.groupby(['industry_code', 'size_category']).size())
except Exception as e:
    print(f"Error creating size categories: {str(e)}")
    restaurant_data['size_category'] = 'unknown'

# Create time variables for analysis
restaurant_data['time'] = restaurant_data['year'] + (restaurant_data['qtr'] - 1) / 4

# Create quarter dummies for seasonal adjustment
restaurant_data = pd.get_dummies(restaurant_data, columns=['qtr'], prefix='quarter')

# Create a policy dummy (1 for observations after 2015 Q3)
restaurant_data['post_policy'] = ((restaurant_data['year'] > policy_implementation[0]) | 
                               ((restaurant_data['year'] == policy_implementation[0]) & 
                                (restaurant_data['quarter_3'] == 1))).astype(int)

# Create a treatment dummy (1 for California)
# The area_fips might be stored as integers, so convert to string first
restaurant_data['area_fips'] = restaurant_data['area_fips'].astype(str)
restaurant_data['treatment'] = (restaurant_data['area_fips'] == "6000").astype(int)

# Double-check treatment assignment
print("\nTreatment assignment check:")
print(restaurant_data.groupby(['area_fips', 'treatment']).size())

# Create interaction terms for DiD and DDD
restaurant_data['treat_post'] = restaurant_data['treatment'] * restaurant_data['post_policy']
restaurant_data['treat_target'] = restaurant_data['treatment'] * restaurant_data['target_industry']
restaurant_data['post_target'] = restaurant_data['post_policy'] * restaurant_data['target_industry']
restaurant_data['treat_post_target'] = restaurant_data['treatment'] * restaurant_data['post_policy'] * restaurant_data['target_industry']

# Save the data for further analysis
restaurant_data.to_csv('restaurant_data_extended.csv', index=False)
print("Saved extended dataset to restaurant_data_extended.csv")

# Create a function for the standard DiD visualization
def plot_did_trends(data, outcome_var, title, output_filename):
    # Prepare data for time series plot by target industry
    pivot_data = pd.pivot_table(
        data,
        index=['data_year', 'time'],
        columns=['area_fips', 'target_industry'],
        values=outcome_var,
        aggfunc='mean'
    ).reset_index()
    
    # Map area_fips to state names for plotting
    area_mapping = {"6000": "California", "48000": "Texas"}
    industry_mapping = {1: "Full-Service Restaurants", 0: "Limited-Service Restaurants"}
    
    # Create visualization of trends
    plt.figure(figsize=(14, 8))
    
    # Plot trends for each area and industry
    for area_code in pivot_data.columns.levels[0]:
        if area_code in ['data_year', 'time']:
            continue
        for industry in pivot_data.columns.levels[1]:
            if (area_code, industry) in pivot_data.columns:
                label = f"{area_mapping.get(area_code, area_code)} - {industry_mapping.get(industry, industry)}"
                line_style = '-' if industry == 1.0 else '--'
                color = 'blue' if area_code == '6000' else 'green'
                plt.plot(pivot_data['time'], pivot_data[(area_code, industry)], 
                         label=label, linewidth=2, linestyle=line_style, color=color if industry == 1.0 else 'orange' if area_code == '6000' else 'red')
    
    # Add vertical line for policy implementation
    policy_time = policy_implementation[0] + (policy_implementation[1] - 1) / 4
    plt.axvline(x=policy_time, color='black', linestyle='--', linewidth=2,
                label='CA Paid Sick Leave (2015 Q3)')
    
    # Mark periods
    plt.axvspan(start_year, policy_time, alpha=0.1, color='green', label='Pre-policy period')
    plt.axvspan(policy_time, end_year + 1, alpha=0.1, color='blue', label='Post-policy period')
    
    plt.title(title, fontsize=16)
    plt.xlabel('Year', fontsize=14)
    plt.ylabel(outcome_var.replace('_', ' ').title(), fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=10, loc='upper left')
    plt.xticks(np.arange(start_year, end_year + 1.25, 0.25), rotation=45)
    plt.tight_layout()
    plt.savefig(output_filename, dpi=300)
    print(f"Saved trend chart to {output_filename}")

# Define a function for running DiD and DDD regressions
def run_regression_analysis(data, outcome_var, model_type='did', include_seasonal=True):
    # Create formula for regression
    if model_type == 'did':
        formula = f"{outcome_var} ~ treatment + post_policy + treat_post"
    elif model_type == 'ddd':
        formula = f"{outcome_var} ~ treatment + post_policy + target_industry + treat_post + treat_target + post_target + treat_post_target"
    
    # Add seasonal controls if requested
    if include_seasonal:
        seasonal_vars = [col for col in data.columns if col.startswith('quarter_')]
        if seasonal_vars:
            formula += " + " + " + ".join(seasonal_vars[:-1])  # Exclude one quarter to avoid perfect collinearity
    
    # Fit the model
    try:
        model = smf.ols(formula=formula, data=data)
        results = model.fit(cov_type='HC3')  # Using robust standard errors
        return results
    except Exception as e:
        print(f"Error in regression analysis: {str(e)}")
        return None

try:
    # 1. Standard DiD for Employment
    print("\nCreating visualizations for employment trends...")
    plot_did_trends(restaurant_data, 'avg_emplvl', 
                    'Restaurant Employment: California vs Texas (2013-2017)', 
                    'employment_trends_by_industry.png')

    # 2. Triple Difference Analysis (DDD)
    print("\nPerforming Triple Difference (DDD) Analysis...")
    ddd_results = run_regression_analysis(restaurant_data, 'avg_emplvl', model_type='ddd')
    if ddd_results:
        print("\nTriple Difference (DDD) Regression Results:")
        print(ddd_results.summary().tables[1])

        # Print key coefficient for interpretation
        ddd_coef = ddd_results.params['treat_post_target']
        ddd_pval = ddd_results.pvalues['treat_post_target']
        print(f"\nDDD Estimate (treat_post_target coefficient): {ddd_coef:.2f} (p={ddd_pval:.4f})")

        if ddd_pval > 0.05:
            print("The triple-difference estimate is not statistically significant, suggesting that full-service restaurants")
            print("did not respond differently to the paid sick leave policy compared to limited-service restaurants.")
        else:
            direction = "positive" if ddd_coef > 0 else "negative"
            print(f"The triple-difference estimate is statistically significant with a {direction} coefficient,")
            print(f"suggesting that full-service restaurants had a {direction} employment response to the policy")
            print("compared to limited-service restaurants.")

    # 3. Alternative Outcomes Analysis - Weekly Wages
    print("\nAnalyzing Alternative Outcome: Weekly Wages...")
    plot_did_trends(restaurant_data, 'avg_wkly_wage', 
                    'Restaurant Weekly Wages: California vs Texas (2013-2017)', 
                    'wage_trends_by_industry.png')

    # Run DiD for wages
    wage_did_results = run_regression_analysis(restaurant_data, 'avg_wkly_wage')
    if wage_did_results:
        print("\nDiD Results for Weekly Wages:")
        print(wage_did_results.summary().tables[1])

        wage_coef = wage_did_results.params['treat_post']
        wage_pval = wage_did_results.pvalues['treat_post']
        print(f"\nDiD Estimate for Wages: {wage_coef:.2f} (p={wage_pval:.4f})")

        if wage_pval > 0.05:
            print("The effect on wages is not statistically significant.")
        else:
            direction = "increased" if wage_coef > 0 else "decreased"
            print(f"The paid sick leave policy significantly {direction} weekly wages.")

    # 4. Heterogeneity Analysis by Restaurant Size
    print("\nPerforming Heterogeneity Analysis by Restaurant Size...")

    # Only proceed if we have size categories
    if 'small' in restaurant_data['size_category'].values:
        # Create subplots for each size category
        plt.figure(figsize=(18, 12))
        gs = gridspec.GridSpec(2, 2, height_ratios=[1, 1])

        size_categories = ['small', 'medium', 'large']
        size_results = {}

        for i, size in enumerate(size_categories):
            # Filter data for this size category
            size_data = restaurant_data[(restaurant_data['size_category'] == size) & (restaurant_data['target_industry'] == 1)]
            
            # Run DiD regression for this size category
            if len(size_data) > 0:
                size_results[size] = run_regression_analysis(size_data, 'avg_emplvl')
                
                # Create plot for this size category
                ax = plt.subplot(gs[i])
                
                # Prepare data for time series plot
                pivot_data = pd.pivot_table(
                    size_data, 
                    index=['data_year', 'time'],
                    columns=['area_fips'],
                    values='avg_emplvl',
                    aggfunc='mean'
                ).reset_index()
                
                # Plot employment trends
                for area_code in pivot_data.columns:
                    if area_code in ['data_year', 'time']:
                        continue
                    label = "California" if area_code == "6000" else "Texas"
                    ax.plot(pivot_data['time'], pivot_data[area_code], label=label, linewidth=2)
                
                # Add vertical line for policy implementation
                policy_time = policy_implementation[0] + (policy_implementation[1] - 1) / 4
                ax.axvline(x=policy_time, color='red', linestyle='--', linewidth=2,
                            label='CA Paid Sick Leave (2015 Q3)')
                
                # Add title and labels
                ax.set_title(f'{size.title()} Restaurants', fontsize=14)
                ax.set_xlabel('Year', fontsize=12)
                ax.set_ylabel('Average Employment', fontsize=12)
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend(fontsize=10)
                
                # Print DiD results for this size category
                if size_results[size]:
                    coef = size_results[size].params['treat_post']
                    pval = size_results[size].pvalues['treat_post']
                    print(f"\nDiD Estimate for {size.title()} Restaurants: {coef:.2f} (p={pval:.4f})")

        # Add an overall title
        plt.suptitle('Heterogeneity by Restaurant Size: Employment Effects of CA Paid Sick Leave', fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig('heterogeneity_by_size.png', dpi=300)
        print("Saved heterogeneity analysis to heterogeneity_by_size.png")
    else:
        print("Skipping heterogeneity analysis - size categories not available")

    # 5. Seasonal Adjustment Analysis
    print("\nPerforming Seasonal Adjustment Analysis...")

    # Filter for full-service restaurants only
    full_service_data = restaurant_data[restaurant_data['target_industry'] == 1].copy()

    # Function to perform seasonal decomposition
    def seasonal_analysis(data, state_fips):
        # Filter data for this state
        state_data = data[data['area_fips'] == state_fips].copy()
        
        # Sort data by time
        state_data = state_data.sort_values('time')
        
        # Create time series for seasonal decomposition
        ts_data = pd.Series(state_data['avg_emplvl'].values, index=state_data['time'])
        
        # Perform seasonal decomposition
        try:
            decomposition = seasonal_decompose(ts_data, model='additive', period=4)
            return state_data, decomposition
        except Exception as e:
            print(f"Error in seasonal decomposition for {state_fips}: {str(e)}")
            return state_data, None

    # Create a figure for seasonal analysis
    plt.figure(figsize=(15, 18))
    gs = gridspec.GridSpec(5, 2)

    # Only proceed if we have enough data points
    if len(full_service_data) >= 8:  # Need at least 2 years of quarterly data
        # Analyze California
        ca_data, ca_decomp = seasonal_analysis(full_service_data, "6000")
        # Analyze Texas
        tx_data, tx_decomp = seasonal_analysis(full_service_data, "48000")

        if ca_decomp and tx_decomp:
            # Plot California
            ax1 = plt.subplot(gs[0, 0])
            ax1.plot(ca_data['time'], ca_data['avg_emplvl'])
            ax1.set_title('California - Original')
            
            ax2 = plt.subplot(gs[1, 0])
            ax2.plot(ca_data['time'], ca_decomp.trend)
            ax2.set_title('California - Trend')
            
            ax3 = plt.subplot(gs[2, 0])
            ax3.plot(ca_data['time'], ca_decomp.seasonal)
            ax3.set_title('California - Seasonal')
            
            ax4 = plt.subplot(gs[3, 0])
            ax4.plot(ca_data['time'], ca_decomp.resid)
            ax4.set_title('California - Residual')
            
            # Plot Texas
            ax5 = plt.subplot(gs[0, 1])
            ax5.plot(tx_data['time'], tx_data['avg_emplvl'])
            ax5.set_title('Texas - Original')
            
            ax6 = plt.subplot(gs[1, 1])
            ax6.plot(tx_data['time'], tx_decomp.trend)
            ax6.set_title('Texas - Trend')
            
            ax7 = plt.subplot(gs[2, 1])
            ax7.plot(tx_data['time'], tx_decomp.seasonal)
            ax7.set_title('Texas - Seasonal')
            
            ax8 = plt.subplot(gs[3, 1])
            ax8.plot(tx_data['time'], tx_decomp.resid)
            ax8.set_title('Texas - Residual')
            
            # Create seasonally adjusted data for DiD
            ca_data['adj_emplvl'] = ca_decomp.trend + ca_decomp.resid
            tx_data['adj_emplvl'] = tx_decomp.trend + tx_decomp.resid
            
            # Combine and plot the seasonally adjusted data
            adj_data = pd.concat([ca_data, tx_data])
            
            ax9 = plt.subplot(gs[4, :])
            for state, color, label in [("6000", "blue", "California"), ("48000", "green", "Texas")]:
                state_data = adj_data[adj_data['area_fips'] == state]
                ax9.plot(state_data['time'], state_data['adj_emplvl'], color=color, label=label)
            
            # Add vertical line for policy implementation
            policy_time = policy_implementation[0] + (policy_implementation[1] - 1) / 4
            ax9.axvline(x=policy_time, color='red', linestyle='--', linewidth=2,
                        label='CA Paid Sick Leave (2015 Q3)')
            
            ax9.set_title('Seasonally Adjusted Employment', fontsize=14)
            ax9.legend()
            
            # Run DiD on seasonally adjusted data
            adj_did_results = run_regression_analysis(adj_data, 'adj_emplvl', include_seasonal=False)
            if adj_did_results:
                print("\nDiD Results for Seasonally Adjusted Employment:")
                print(adj_did_results.summary().tables[1])
                
                adj_coef = adj_did_results.params['treat_post']
                adj_pval = adj_did_results.pvalues['treat_post']
                print(f"\nDiD Estimate for Seasonally Adjusted Employment: {adj_coef:.2f} (p={adj_pval:.4f})")
    else:
        print("Skipping seasonal adjustment analysis - insufficient data points")

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('seasonal_adjustment_analysis.png', dpi=300)
    print("Saved seasonal adjustment analysis to seasonal_adjustment_analysis.png")

except Exception as e:
    import traceback
    print(f"Error during analysis: {str(e)}")
    print(traceback.format_exc())

print("\nExtended analysis complete!")


Run the econ140.py to produce the same results
- The output will be 5 files
-   - employment_trends_by_industry.png
    - heterogeneity_by_size.png
    - Restaurant_data_extended.csv
    - wage_trends_by_industry.png

This is the terminal output

Performing Triple Difference (DDD) Analysis...

Triple Difference (DDD) Regression Results:
=====================================================================================
                        coef    std err          z      P>|z|      [0.025      0.975]
-------------------------------------------------------------------------------------
Intercept          1.989e+05   5.44e+04      3.660      0.000    9.24e+04    3.05e+05
quarter_1[T.True] -6415.7333   5.07e+04     -0.126      0.899   -1.06e+05     9.3e+04
quarter_2[T.True]   199.6800   5.16e+04      0.004      0.997   -1.01e+05    1.01e+05
quarter_3[T.True] -2433.6886   5.23e+04     -0.047      0.963   -1.05e+05       1e+05
treatment          3.073e+04   6.83e+04      0.450      0.653   -1.03e+05    1.65e+05
post_policy        2.512e+04   7.22e+04      0.348      0.728   -1.16e+05    1.67e+05
target_industry   -5.479e+04   5.78e+04     -0.948      0.343   -1.68e+05    5.85e+04
treat_post         1666.4057   1.09e+05      0.015      0.988   -2.13e+05    2.16e+05
treat_target       2.683e+04    9.3e+04      0.288      0.773   -1.55e+05    2.09e+05
post_target        -1.48e+04   9.17e+04     -0.161      0.872   -1.95e+05    1.65e+05
treat_post_target  2686.5853   1.47e+05      0.018      0.985   -2.86e+05    2.91e+05
=====================================================================================

DDD Estimate (treat_post_target coefficient): 2686.59 (p=0.9854)
The triple-difference estimate is not statistically significant, suggesting that full-service restaurants
did not respond differently to the paid sick leave policy compared to limited-service restaurants.

Analyzing Alternative Outcome: Weekly Wages...
Saved trend chart to wage_trends_by_industry.png

DiD Results for Weekly Wages:
=====================================================================================
                        coef    std err          z      P>|z|      [0.025      0.975]
-------------------------------------------------------------------------------------
Intercept           272.5823     42.935      6.349      0.000     188.432     356.733
quarter_1[T.True]   -17.9600     64.946     -0.277      0.782    -145.252     109.332
quarter_2[T.True]    -8.0600     63.215     -0.128      0.899    -131.960     115.840
quarter_3[T.True]     5.4275     64.791      0.084      0.933    -121.560     132.415
treatment           225.3455     74.483      3.025      0.002      79.362     371.329
post_policy          20.3686     31.207      0.653      0.514     -40.796      81.533
treat_post         -170.8121     86.655     -1.971      0.049    -340.653      -0.972
=====================================================================================

DiD Estimate for Wages: -170.81 (p=0.0487)
The paid sick leave policy significantly decreased weekly wages.

Performing Heterogeneity Analysis by Restaurant Size...

DiD Estimate for Small Restaurants: 0.00 (p=nan)

DiD Estimate for Medium Restaurants: -17.85 (p=0.2416)

DiD Estimate for Large Restaurants: 13076.82 (p=0.0954)
Saved heterogeneity analysis to heterogeneity_by_size.png

Performing Seasonal Adjustment Analysis...

DiD Results for Seasonally Adjusted Employment:
===============================================================================
                  coef    std err          z      P>|z|      [0.025      0.975]
-------------------------------------------------------------------------------
Intercept    1.536e+05   3.81e+04      4.035      0.000     7.9e+04    2.28e+05
treatment    6.226e+04   6.57e+04      0.948      0.343   -6.64e+04    1.91e+05
post_policy -1.047e+04   5.49e+04     -0.191      0.849   -1.18e+05     9.7e+04
treat_post  -4241.6870   9.46e+04     -0.045      0.964    -1.9e+05    1.81e+05
===============================================================================

DiD Estimate for Seasonally Adjusted Employment: -4241.69 (p=0.9642)
Saved seasonal adjustment analysis to seasonal_adjustment_analysis.png

Creating summary chart of all findings...
Saved summary chart to results_summary_chart.png

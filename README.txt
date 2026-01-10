===========================================================================
                        ERROR ANALYSIS TOOL README
===========================================================================

1. PURPOSE
---------------------------------------------------------------------------
Verifies the accuracy of 3D antenna pattern interpolation by comparing a 
Predicted CSV against a Ground Truth CSV.

2. INPUT
---------------------------------------------------------------------------
Both CSV files must share the same angular grid (step size) and contain 
these exact headers:

  1. Phi[deg]
  2. Theta[deg]
  3. dB10normalize(GainTotal) 
     (Rename your gain column to this if necessary)


4. RESULTS
---------------------------------------------------------------------------
RMSE (Root Mean Sq Error):
   - The primary accuracy metric.

Mean Bias:
   - The average tendency of the prediction.
   - Positive (+): Optimistic (Predicting higher signal than reality).
   - Negative (-): Conservative (Predicting lower signal than reality).

Error Heatmaps:
   - Left/Center: Visual comparison of patterns.
   - Right (Error): 
       - Blue/Black: Minimal error.
       - Red/Yellow: Indicates a mismatch.

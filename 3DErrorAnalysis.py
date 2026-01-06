import pandas as pd
import numpy as np
import sys
import os
import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import cm

# ==========================================
#           VISUALIZATION CLASSES
# ==========================================

class PlotPanel(tk.Frame):
    """A Tkinter frame that holds a Matplotlib figure."""
    def __init__(self, parent, title):
        super().__init__(parent)
        self.figure = Figure(figsize=(4, 5), dpi=100)
        self.figure.set_tight_layout(True)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title, fontsize=10)
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

class AntennaComparisonViewer:
    def __init__(self, grid_interp, grid_orig, grid_error, mse, rmse, mean_bias):
        self.root = tk.Tk()
        self.root.title(f"Antenna Pattern Comparison (MSE: {mse:.4f})")
        self.root.geometry("1400x600")
        
        # Data
        self.grid_interp = grid_interp
        self.grid_orig = grid_orig
        self.grid_error = grid_error
        
        # Layout: 1 Row, 3 Columns
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(0, weight=1) # Plot area
        self.root.rowconfigure(1, weight=0) # Stats area

        # Extent for Plots: Theta (x) 0..180, Phi (y) 0..360
        self.extent = [0, 180, 0, 360] 

        # --- Plot 1: Interpolated ---
        self.p1 = PlotPanel(self.root, "Predicted Pattern (Interpolated)")
        self.p1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self._draw_heatmap(self.p1, self.grid_interp, cmap=cm.nipy_spectral, label="Gain [dB]")

        # --- Plot 2: Original ---
        self.p2 = PlotPanel(self.root, "Actual Pattern (Original)")
        self.p2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._draw_heatmap(self.p2, self.grid_orig, cmap=cm.nipy_spectral, label="Gain [dB]")

        # --- Plot 3: Error ---
        self.p3 = PlotPanel(self.root, "Absolute Error")
        self.p3.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        # Using 'jet' for error to highlight differences (blue=low, red=high)
        self._draw_heatmap(self.p3, self.grid_error, cmap=cm.jet, label="Abs Error [dB]")

        # --- Stats Bar ---
        stats_frame = ttk.Frame(self.root)
        stats_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        
        # Determine Bias Label
        if mean_bias > 0:
            bias_desc = "Optimistic"
        else:
            bias_desc = "Conservative"

        lbl_text = (f"COMPARISON STATISTICS  |  "
                    f"MSE: {mse:.4f}  |  "
                    f"RMSE: {rmse:.4f}  |  "
                    f"Mean Bias: {mean_bias:.4f} dB ({bias_desc})")
        
        ttk.Label(stats_frame, text=lbl_text, font=("Arial", 11, "bold")).pack()

    def _draw_heatmap(self, panel, data, cmap, label):
        #Helper to draw the 2D heatmap on a panel
        vmin = np.nanmin(data)
        vmax = np.nanmax(data)

        im = panel.ax.imshow(
            data,
            extent=self.extent,
            aspect='auto',
            origin='lower',
            cmap=cmap,
            interpolation='bilinear',
            vmin=vmin, vmax=vmax
        )
        
        panel.ax.set_xlabel("Theta (degree)")
        panel.ax.set_ylabel("Phi (degree)")
        panel.figure.colorbar(im, ax=panel.ax, label=label)

    def show(self):
        self.root.mainloop()

# ==========================================
#           CALCULATION LOGIC
# ==========================================

def calculate_antenna_mse(file_interp, file_orig):
    # Alignment determined based on 'Phi[deg]' and 'Theta[deg]' columns.
    
    print(f"Loading Interpolated Data: {file_interp}")
    print(f"Loading Original Data:     {file_orig}")

    try:
        # Load DataFrames
        df_interp = pd.read_csv(file_interp)
        df_orig = pd.read_csv(file_orig)
        
        # 1. Clean Column Names
        df_interp.columns = [c.strip() for c in df_interp.columns]
        df_orig.columns = [c.strip() for c in df_orig.columns]

        # 2. Check for required columns
        target_col = 'dB10normalize(GainTotal)'
        req_cols = ['Phi[deg]', 'Theta[deg]', target_col]
        
        for df, name in [(df_interp, "Interpolated"), (df_orig, "Original")]:
            if not all(col in df.columns for col in req_cols):
                print(f"Error: {name} file missing required columns: {req_cols}")
                # Debug helper: print available columns
                print(f"Available columns: {list(df.columns)}")
                return

        # 3. Merge DataFrames (Inner Join)
        merged = pd.merge(
            df_orig, 
            df_interp, 
            on=['Phi[deg]', 'Theta[deg]'], 
            suffixes=('_orig', '_interp')
        )

        if merged.empty:
            print("Error: No matching Phi/Theta coordinates found between files.")
            print("Check if angle ranges (e.g. -180 vs 0..360) match.")
            return

        print(f"Aligned {len(merged)} data points for comparison.")

        # 4. Calculate Squared Error
        col_orig = f"{target_col}_orig"
        col_interp = f"{target_col}_interp"
        
        merged['diff'] = merged[col_interp] - merged[col_orig] # Bias (Signed: Pred - Actual)
        #Useful for determining if interpolation is over or under estimation
        merged['sq_error'] = merged['diff'] ** 2
        merged['abs_error'] = merged['diff'].abs() 
        
        # 5. Compute MSE and Mean Bias
        mse = merged['sq_error'].mean()
        rmse = mse ** 0.5
        mean_bias = merged['diff'].mean() # Calculate Mean Bias
        
        # 6. Report Results
        print("-" * 40)
        print(f"Mean Squared Error (MSE):      {mse:.6f}")
        print(f"Root Mean Squared Error (RMSE): {rmse:.6f}")
        
        # Bias Report
        if mean_bias > 0:
            print(f"Mean Bias:                     {mean_bias:.6f} dB (Optimistic)")
        else:
            print(f"Mean Bias:                     {mean_bias:.6f} dB (Conservative)")
        print("-" * 40)

        # Optional: Show worst mismatches
        print("\nTop 5 Largest Differences:")
        print(merged.nlargest(5, 'sq_error')[['Phi[deg]', 'Theta[deg]', col_orig, col_interp, 'diff']])

        # ==========================================
        #           VISUALIZATION
        # ==========================================
        print("\nPreparing Visualization...")
        
        # Pivot DataFrames to 2D Matrix for Heatmaps
        # Index = Phi (Y-axis), Columns = Theta (X-axis)
        grid_interp = merged.pivot(index='Phi[deg]', columns='Theta[deg]', values=col_interp)
        grid_orig = merged.pivot(index='Phi[deg]', columns='Theta[deg]', values=col_orig)
        grid_error = merged.pivot(index='Phi[deg]', columns='Theta[deg]', values='abs_error')
        
        # Sort indices to ensure plots are oriented correctly (0 to 360 ascending)
        grid_interp.sort_index(axis=0, inplace=True) 
        grid_interp.sort_index(axis=1, inplace=True)
        
        # Apply same sort to others
        grid_orig = grid_orig.reindex_like(grid_interp)
        grid_error = grid_error.reindex_like(grid_interp)

        # Launch GUI
        app = AntennaComparisonViewer(
            grid_interp.values, 
            grid_orig.values, 
            grid_error.values, 
            mse, 
            rmse,
            mean_bias # Pass mean bias to GUI
        )
        app.show()

    except FileNotFoundError as e:
        print(f"Error: File not found - {e.filename}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # USER INPUT! ENTER FILEPATH BELOW
    file_path_interpolated = r"C:\Users\paulw\Downloads\ComparisonValues\Gain Norm - Pyramidal Horn\3DInterpolatedSummingPyramid.csv"
    file_path_original = r"C:\Users\paulw\Downloads\ComparisonValues\Gain Norm - Pyramidal Horn\3DPolarPlotPyramid.csv"
    
    # Check if files exist before running
    if not os.path.exists(file_path_interpolated) or not os.path.exists(file_path_original):
        print("Please update the file paths in the script to point to your CSV files.")
        # Debug helper: print what python sees
        print(f"Looking for: {file_path_interpolated}")
    else:
        calculate_antenna_mse(file_path_interpolated, file_path_original)
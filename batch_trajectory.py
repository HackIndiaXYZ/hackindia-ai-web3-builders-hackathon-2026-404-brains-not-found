from trajectory_engine import match_plates_across_cameras, compute_heatmap

if __name__ == '__main__':
    print("Running trajectory matching...")
    match_plates_across_cameras()
    
    print("Computing heatmap...")
    compute_heatmap()
    
    print("Done!")

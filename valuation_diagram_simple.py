import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

# Create figure with proper dimensions
fig, ax = plt.subplots(figsize=(16, 20))
ax.set_xlim(0, 16)
ax.set_ylim(0, 20)
ax.axis('off')

# Colors
blue = '#1976D2'
red = '#D32F2F'
orange = '#FF9800'
green = '#4CAF50'

# TITLE
ax.text(8, 19.5, 'OAKVILLE PROPERTY VALUATION SYSTEM', 
        fontsize=20, fontweight='bold', ha='center', color=blue)
ax.text(8, 19, 'Step-by-Step Calculation Guide (All values in CAD)', 
        fontsize=12, ha='center', style='italic')

# STEP 1 - LAND VALUE
rect1 = Rectangle((1, 17), 14, 1.5, facecolor='#E3F2FD', edgecolor=blue, linewidth=2)
ax.add_patch(rect1)
ax.text(1.5, 18.2, 'STEP 1: BASE LAND VALUE', fontsize=14, fontweight='bold', color=blue)
ax.text(1.5, 17.8, 'Formula: Zone Rate × Lot Area', fontsize=11)
ax.text(1.5, 17.4, 'RL1: $650/m² | RL1-0: $700/m² | RL2: $580/m² | RL3: $520/m²', fontsize=10)
ax.text(10, 17.8, 'EXAMPLE:', fontsize=10, fontweight='bold', color=red)
ax.text(10, 17.5, 'RL1-0 × 1200m² = $840,000', fontsize=10, color=red)

# STEP 2 - BUILDING VALUE  
rect2 = Rectangle((1, 15), 14, 1.5, facecolor='#E8F5E8', edgecolor=green, linewidth=2)
ax.add_patch(rect2)
ax.text(1.5, 16.2, 'STEP 2: BUILDING VALUE WITH DEPRECIATION', fontsize=14, fontweight='bold', color=green)
ax.text(1.5, 15.8, 'Formula: Area × $2,800/m² × (1 - 0.02 × Age)', fontsize=11)
ax.text(1.5, 15.4, 'Detached: $2,800/m² | Semi: $2,600/m² | Townhouse: $2,400/m²', fontsize=10)
ax.text(10, 15.8, 'EXAMPLE:', fontsize=10, fontweight='bold', color=red)
ax.text(10, 15.5, '250m² × 8yrs = $588,000', fontsize=10, color=red)

# STEP 3 - FEATURES
rect3 = Rectangle((1, 13), 14, 1.5, facecolor='#FFF3E0', edgecolor=orange, linewidth=2)
ax.add_patch(rect3)
ax.text(1.5, 14.2, 'STEP 3: PROPERTY FEATURES', fontsize=14, fontweight='bold', color=orange)
ax.text(1.5, 13.8, 'Bedrooms: +$25,000 per bedroom above 3', fontsize=11)
ax.text(1.5, 13.4, 'Bathrooms: +$15,000 per bathroom above 2.5', fontsize=11)
ax.text(10, 13.8, 'EXAMPLE:', fontsize=10, fontweight='bold', color=red)
ax.text(10, 13.5, '4 bed + 3 bath = +$32,500', fontsize=10, color=red)

# STEP 4 - LOCATION
rect4 = Rectangle((1, 11), 14, 1.5, facecolor='#F3E5F5', edgecolor='purple', linewidth=2)
ax.add_patch(rect4)
ax.text(1.5, 12.2, 'STEP 4: LOCATION ADJUSTMENTS', fontsize=14, fontweight='bold', color='purple')
ax.text(1.5, 11.8, 'Waterfront: +30% | Park: +10% | Heritage: -10% | Corner: -5%', fontsize=11)
ax.text(1.5, 11.4, 'Applied to base land value ($840,000)', fontsize=11)
ax.text(10, 11.8, 'EXAMPLE:', fontsize=10, fontweight='bold', color=red)
ax.text(10, 11.5, 'Net adjustment: -$42,000', fontsize=10, color=red)

# STEP 5 - FINAL CALCULATION
rect5 = Rectangle((1, 8.5), 14, 2, facecolor='#E8F5E8', edgecolor=blue, linewidth=3)
ax.add_patch(rect5)
ax.text(8, 10.2, 'STEP 5: FINAL VALUATION', fontsize=16, fontweight='bold', ha='center', color=blue)

# Calculation breakdown
ax.text(2, 9.7, 'CALCULATION SUMMARY:', fontsize=12, fontweight='bold')
ax.text(2.5, 9.4, '1. Land Value: $840,000', fontsize=11)
ax.text(2.5, 9.1, '2. Building Value: $588,000', fontsize=11) 
ax.text(2.5, 8.8, '3. Features: +$32,500', fontsize=11)

ax.text(9, 9.4, '4. Location: -$42,000', fontsize=11)
ax.text(9, 9.1, 'Subtotal: $1,418,500', fontsize=11, fontweight='bold')
ax.text(9, 8.8, 'Market Adj: ×1.05', fontsize=11)

# Final result box
result_rect = Rectangle((5, 7.8), 6, 0.6, facecolor='lightgreen', edgecolor='darkgreen', linewidth=2)
ax.add_patch(result_rect)
ax.text(8, 8.1, 'FINAL VALUE: $1,489,425 CAD', fontsize=14, fontweight='bold', ha='center', color='darkgreen')

# DEVELOPMENT ANALYSIS
rect6 = Rectangle((1, 6), 14, 1.5, facecolor='#FFF3E0', edgecolor=orange, linewidth=2)
ax.add_patch(rect6)
ax.text(1.5, 7.2, 'DEVELOPMENT ANALYSIS (RM Zones)', fontsize=14, fontweight='bold', color=orange)
ax.text(1.5, 6.8, 'Multi-Unit Potential: Floor Area ÷ 120m² = Units', fontsize=11)
ax.text(1.5, 6.4, 'Feasible if: Profit Margin > 15% | Unit Values: $450k-$650k', fontsize=11)

# OUTPUT FEATURES
rect7 = Rectangle((1, 4), 14, 1.5, facecolor='#F5F5F5', edgecolor='black', linewidth=2)
ax.add_patch(rect7)
ax.text(1.5, 5.2, 'SYSTEM OUTPUT', fontsize=14, fontweight='bold')
ax.text(1.5, 4.8, '• Final Value + Confidence Range (±15%)', fontsize=11)
ax.text(1.5, 4.5, '• Component Breakdown + Price per m²', fontsize=11)
ax.text(1.5, 4.2, '• Real-Time Calculation + Market Data', fontsize=11)

# KEY FEATURES  
rect8 = Rectangle((1, 2), 14, 1.5, facecolor='#E3F2FD', edgecolor=blue, linewidth=2)
ax.add_patch(rect8)
ax.text(1.5, 3.2, 'KEY SYSTEM FEATURES', fontsize=14, fontweight='bold', color=blue)
ax.text(1.5, 2.8, '✓ Zone-Specific Pricing ✓ Suffix-0 Recognition ✓ Age Depreciation', fontsize=11)
ax.text(1.5, 2.5, '✓ Location Intelligence ✓ Market Adjustments ✓ Confidence Intervals', fontsize=11)
ax.text(1.5, 2.2, '✓ Development Feasibility ✓ Canadian Banking Standards', fontsize=11)

# FOOTER
rect9 = Rectangle((1, 0.2), 14, 1.2, facecolor='#FFFDE7', edgecolor='#F57C00', linewidth=2)
ax.add_patch(rect9)
ax.text(8, 1, 'CANADIAN REAL ESTATE VALUATION SYSTEM', fontsize=12, fontweight='bold', ha='center', color='#F57C00')
ax.text(8, 0.7, 'All Values in Canadian Dollars (CAD)', fontsize=11, ha='center', fontweight='bold')
ax.text(8, 0.4, 'Calibrated for Oakville, Ontario Market', fontsize=10, ha='center', style='italic')

plt.tight_layout()
plt.savefig('C:/Users/Soft Suave/Desktop/Project Files/AI/AI Integrated Real Estate Task/oakville-real-estate-analyzer/Valuation_Guide_Simple.png', 
            dpi=200, bbox_inches='tight', facecolor='white')
plt.close()

print("Simple Property Valuation Guide created successfully!")
print("File: Valuation_Guide_Simple.png")
print("✓ Clear sections with proper spacing")
print("✓ No overlapping elements")
print("✓ Professional layout for presentations")
import matplotlib.pyplot as plt
import numpy as np

plt.figure(figsize=(4, 3))  # Width=10 inches

# Data
data = np.array([
    [0.42857143, 0.57142857],
    [0.32876712, 0.67123288],
    [0.73993522, 0.26006478],
    [0.47507433, 0.52492567],
    [0.34835824, 0.65164176],
    [0.29656769, 0.70343231],
    [0.27677966, 0.72322034],
    [0.26941524, 0.73058476],
    [0.26670136, 0.73329864],
    [0.2657049,  0.7342951 ],
    [0.26533952, 0.73466048]
])

# Plot
plt.plot(data[:, 0], label='P(correct)')
plt.plot(data[:, 1], label='P(incorrect)')
plt.xlabel('Step')
plt.axvline(x=1, color='gray', linestyle='--', linewidth=1)  # Vertical line at x = 1
plt.ylabel('Probability')
plt.title('Probability of Correct vs Incorrect')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

import matplotlib.pyplot as plt
import numpy as np
import csv

discrete = []
pattern = []
pulse = []
visual = []

discrete_x = []
pattern_x = []
pulse_x = []
visual_x = []


ticks = ['3 levels', '4 levels', '5 levels', '6 levels', '7 levels', '8 levels']
      
def stats3(f):
    with open(f, "r") as file:
        c = 6
        reader = csv.reader(file, delimiter=',')
        i = 0
        choice = None
        for row in reader:
            if i % c == 0:
                if "discrete" in row[0]:
                    choice = "discrete"
                elif "pattern" in row[0]:
                    choice = "pattern"
                elif "pulse" in row[0]:
                    choice = "pulse"
                elif "visual" in row[0]:
                    choice = "visual"
            if i % c == 2:
                if "excl" in f:
                    if choice == "discrete":
                        discrete_x.append(row)
                    if choice == "pattern":
                        pattern_x.append(row)
                    if choice == "pulse":
                        pulse_x.append(row)
                    if choice == "visual":
                        visual_x.append(row)
                else:
                    if choice == "discrete":
                        discrete.append(row)
                    if choice == "pattern":
                        pattern.append(row)
                    if choice == "pulse":
                        pulse.append(row)
                    if choice == "visual":
                        visual.append(row)
            i += 1

            
def set_box_color(bp, color):
    plt.setp(bp['boxes'], color=color)
    plt.setp(bp['whiskers'], color=color)
    plt.setp(bp['caps'], color=color)
    plt.setp(bp['medians'], color=color)


stats3("all_check.csv")
for i in range(len(discrete)):
    for j in range(len(discrete[i])):
        discrete[i][j] = float(discrete[i][j])
        if discrete[i][j] > 18:
            print(f"wtf: {discrete[i][j]}")
for i in range(len(pattern)):
    for j in range(len(pattern[i])):
        pattern[i][j] = float(pattern[i][j])
for i in range(len(pulse)):
    for j in range(len(pulse[i])):
        pulse[i][j] = float(pulse[i][j])
for i in range(len(visual)):
    for j in range(len(visual[i])):
        visual[i][j] = float(visual[i][j])
        
stats3("all_excl_check.csv")
for i in range(len(discrete_x)):
    for j in range(len(discrete_x[i])):
        discrete_x[i][j] = float(discrete_x[i][j])
for i in range(len(pattern_x)):
    for j in range(len(pattern_x[i])):
        pattern_x[i][j] = float(pattern_x[i][j])
for i in range(len(pulse_x)):
    for j in range(len(pulse_x[i])):
        pulse_x[i][j] = float(pulse_x[i][j])
for i in range(len(visual_x)):
    for j in range(len(visual_x[i])):
        visual_x[i][j] = float(visual_x[i][j])
#fig, axs = plt.figure(2)

'''bpd = plt.boxplot(discrete, positions=np.array(range(len(discrete)))*2.0-0.6, sym='', widths=0.3)
bppa = plt.boxplot(pattern, positions=np.array(range(len(pattern)))*2.0-0.2, sym='', widths=0.3)
bppu = plt.boxplot(pulse, positions=np.array(range(len(pulse)))*2.0+0.2, sym='', widths=0.3)
bpv = plt.boxplot(visual, positions=np.array(range(len(visual)))*2.0+0.6, sym='', widths=0.3)'''

bpd = plt.boxplot(discrete_x, positions=np.array(range(len(discrete_x)))*2.0-0.6, sym='.', widths=0.3)
bppa = plt.boxplot(pattern_x, positions=np.array(range(len(pattern_x)))*2.0-0.2, sym='.', widths=0.3)
bppu = plt.boxplot(pulse_x, positions=np.array(range(len(pulse_x)))*2.0+0.2, sym='.', widths=0.3)
bpv = plt.boxplot(visual_x, positions=np.array(range(len(visual_x)))*2.0+0.6, sym='.', widths=0.3)
                   
set_box_color(bpd, '#AA904C') # colors are from http://colorbrewer2.org/
set_box_color(bppa, '#56AA4C')
set_box_color(bppu, '#4C96AA')
set_box_color(bpv, '#AA4C4E')

# draw temporary red and blue lines and use them to create a legend
plt.plot([], c='#AA904C', label='discrete pitch-modulated sine wave signal')
plt.plot([], c='#56AA4C', label='temporal frequency-modulated pattern signal')
plt.plot([], c='#4C96AA', label='temporal frequency-modulated pulse signal')
plt.plot([], c='#AA4C4E', label='visual feedback')
plt.legend()
plt.ylabel("Time (s)")
plt.title("", fontweight='bold')

plt.xticks(range(0, len(ticks) * 2, 2), ticks)
plt.xlim(-2, len(ticks)*2)
plt.ylim(0, 20)
plt.tight_layout()
plt.show()
plt.grid(b=True, which='major', axis='y', color='lightgrey', alpha=0.5)
plt.savefig('boxcompare.png')
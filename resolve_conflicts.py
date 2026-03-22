import re

with open('mygame_client.py', 'r') as f:
    lines = f.readlines()

new_lines = []
state = 'normal' # normal, upstream, stashed

for line in lines:
    if line.startswith('<<<<<<< Updated upstream'):
        state = 'upstream'
    elif line.startswith('======='):
        if state == 'upstream':
            state = 'stashed'
        else:
            new_lines.append(line)
    elif line.startswith('>>>>>>> Stashed changes'):
        if state == 'stashed':
            state = 'normal'
        else:
            new_lines.append(line)
    else:
        if state == 'normal' or state == 'upstream':
            new_lines.append(line)

with open('mygame_client.py', 'w') as f:
    f.writelines(new_lines)
print("Conflicts resolved by keeping upstream.")

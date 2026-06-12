import sys
sys.path.insert(0, '.')
from comlab_v3.engine import neighbors

blocked = set()
print("Neighbors of (6, 2):", neighbors((6, 2), blocked))
print("Neighbors of (3, 2):", neighbors((3, 2), blocked))

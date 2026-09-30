from dataclasses import dataclass
from typing import List

@dataclass
class Board:
   grid: List[List[int]]
   # self.grid : List[List[int]] = grid

   # альтернативный конструктор
   @classmethod
   def create_empty(cls) -> 'Board': #forward reference, так как класс еще не определен
      return cls(grid=[[0, 0, 0], [0, 0, 0], [0, 0, 0]])
   
   def get_cell(self, row: int, col: int) -> int:
      return self.grid[row][col]

   def has_empty_cells(self) -> bool:
      for i in range(3):
         for j in range(3):
            if self.grid[i][j] == 0:
               return True
      return False

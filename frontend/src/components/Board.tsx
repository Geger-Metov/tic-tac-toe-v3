import type { Cell, Grid } from "../api/types";

const SIZE = 300;
const STEP = SIZE / 3;

// prettier-ignore
const LINES: [number, number][][] = [
  [[0, 0], [0, 1], [0, 2]],
  [[1, 0], [1, 1], [1, 2]],
  [[2, 0], [2, 1], [2, 2]],
  [[0, 0], [1, 0], [2, 0]],
  [[0, 1], [1, 1], [2, 1]],
  [[0, 2], [1, 2], [2, 2]],
  [[0, 0], [1, 1], [2, 2]],
  [[0, 2], [1, 1], [2, 0]],
];

/** Выигрышная линия (если есть) — для зачёркивания. */
function findWinningLine(grid: Grid): [number, number][] | null {
  for (const line of LINES) {
    const [a, b, c] = line.map(([r, col]) => grid[r][col]);
    if (a !== 0 && a === b && b === c) return line;
  }
  return null;
}

const center = (index: number) => index * STEP + STEP / 2;
const symbolName = (cell: Cell) =>
  cell === 1 ? "крестик" : cell === -1 ? "нолик" : "пусто";

function Mark({ cell, row, col }: { cell: Cell; row: number; col: number }) {
  const cx = center(col);
  const cy = center(row);
  // pathLength=1 + dash-анимация в CSS: штрих «прорисовывается» при появлении.
  if (cell === 1) {
    return (
      <g className="mark mark-x">
        <path
          pathLength={1}
          d={`M ${cx - 27} ${cy - 26} Q ${cx} ${cy + 1} ${cx + 26} ${cy + 28}`}
        />
        <path
          pathLength={1}
          d={`M ${cx + 27} ${cy - 27} Q ${cx - 1} ${cy} ${cx - 28} ${cy + 26}`}
        />
      </g>
    );
  }
  return (
    <g className="mark mark-o">
      <path
        pathLength={1}
        d={`M ${cx + 2} ${cy - 29} C ${cx + 34} ${cy - 30} ${cx + 33} ${cy + 31} ${cx - 1} ${cy + 29}
            C ${cx - 33} ${cy + 28} ${cx - 33} ${cy - 28} ${cx + 7} ${cy - 27}`}
      />
    </g>
  );
}

interface BoardProps {
  grid: Grid;
  /** Клик по клетке; undefined — доска только для просмотра. */
  onCellClick?: (row: number, col: number) => void;
  /** Можно ли сейчас ходить (иначе клетки неактивны). */
  interactive?: boolean;
}

export function Board({ grid, onCellClick, interactive = false }: BoardProps) {
  const win = findWinningLine(grid);

  return (
    <div className="board">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="board-art"
        aria-hidden="true"
      >
        {/* сетка — четыре «карандашные» линии с лёгким изгибом */}
        <g className="board-lines">
          <path d={`M ${STEP} 8 Q ${STEP + 3} 150 ${STEP - 2} 292`} />
          <path
            d={`M ${2 * STEP} 6 Q ${2 * STEP - 3} 150 ${2 * STEP + 2} 294`}
          />
          <path d={`M 8 ${STEP} Q 150 ${STEP + 3} 292 ${STEP - 2}`} />
          <path
            d={`M 6 ${2 * STEP} Q 150 ${2 * STEP - 3} 294 ${2 * STEP + 2}`}
          />
        </g>
        {grid.flatMap((row, r) =>
          row.map((cell, c) =>
            cell === 0 ? null : (
              <Mark key={`${r}-${c}-${cell}`} cell={cell} row={r} col={c} />
            ),
          ),
        )}
        {win && (
          <path
            className="strike"
            pathLength={1}
            d={`M ${center(win[0][1]) - (win[2][1] - win[0][1]) * 14} ${center(win[0][0]) - (win[2][0] - win[0][0]) * 14}
                L ${center(win[2][1]) + (win[2][1] - win[0][1]) * 14} ${center(win[2][0]) + (win[2][0] - win[0][0]) * 14}`}
          />
        )}
      </svg>

      <div className="board-cells">
        {grid.flatMap((row, r) =>
          row.map((cell, c) => (
            <button
              key={`${r}-${c}`}
              type="button"
              className="cell"
              disabled={!interactive || cell !== 0}
              aria-label={`Строка ${r + 1}, столбец ${c + 1}: ${symbolName(cell)}`}
              onClick={() => onCellClick?.(r, c)}
            />
          )),
        )}
      </div>
    </div>
  );
}

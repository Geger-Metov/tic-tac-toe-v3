import { expect, test } from "@playwright/test";
import {
  FINISHED,
  cell,
  crosses,
  noughts,
  playMove,
  playUntilFinished,
  register,
  startGame,
  status,
} from "./helpers.ts";

test.describe("игра с компьютером", () => {
  test.beforeEach(async ({ page }) => {
    await register(page);
  });

  test("начало партии: ходит игрок, доска пустая", async ({ page }) => {
    await startGame(page);

    await expect(page.getByRole("button", { name: /: пусто$/ })).toHaveCount(9);
    await expect(cell(page, 1, 1)).toBeEnabled();
    await expect(
      page.getByRole("button", { name: "Новая партия" }),
    ).toBeVisible();
  });

  test("после хода игрока компьютер отвечает ноликом", async ({ page }) => {
    await startGame(page);

    await playMove(page, 2, 2);

    await expect(crosses(page)).toHaveCount(1);
    await expect(noughts(page)).toHaveCount(1);
    await expect(status(page)).toHaveText("Ваш ход");
    // Занятая клетка больше не доступна.
    await expect(cell(page, 2, 2)).toBeDisabled();
  });

  test("партия продолжается после перезагрузки страницы", async ({ page }) => {
    await startGame(page);
    await playMove(page, 1, 1);

    await page.reload();

    await expect(crosses(page)).toHaveCount(1);
    await expect(noughts(page)).toHaveCount(1);
    await expect(status(page)).toHaveText("Ваш ход");
  });

  test("партия доигрывается до конца, компьютер не проигрывает", async ({
    page,
  }) => {
    await startGame(page);

    const result = await playUntilFinished(page);

    // Минимакс не проигрывает: остаётся ничья или победа компьютера.
    expect(result).toMatch(/^(Ничья|Победил компьютер)$/);
    await expect(status(page)).toHaveText(FINISHED);
    // По окончании ходить нельзя ни в одну клетку.
    await expect(page.locator("button.cell:enabled")).toHaveCount(0);
  });

  test("«Новая партия» начинает с чистой доски", async ({ page }) => {
    await startGame(page);
    await playMove(page, 2, 2);

    await page.getByRole("button", { name: "Новая партия" }).click();

    await expect(status(page)).toHaveText("Ваш ход");
    await expect(page.getByRole("button", { name: /: пусто$/ })).toHaveCount(9);
    await expect(crosses(page)).toHaveCount(0);
    await expect(noughts(page)).toHaveCount(0);
  });

  test("после окончания партии можно сыграть новую", async ({ page }) => {
    await startGame(page);
    await playUntilFinished(page);

    await page.getByRole("button", { name: "Новая партия" }).click();

    await expect(status(page)).toHaveText("Ваш ход");
    await expect(cell(page, 1, 1)).toBeEnabled();
  });
});

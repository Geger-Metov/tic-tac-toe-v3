import { expect } from "@playwright/test";
import type { Locator, Page } from "@playwright/test";

export const PASSWORD = "secret123";

/** Каждый тест работает со своим пользователем: тесты не зависят друг от друга. */
export function uniqueLogin(prefix = "e2e"): string {
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${Date.now().toString(36)}-${rand}`;
}

export const status = (page: Page): Locator =>
  page.getByRole("heading", { level: 1 });

export const crosses = (page: Page): Locator =>
  page.getByRole("button", { name: /: крестик$/ });

export const noughts = (page: Page): Locator =>
  page.getByRole("button", { name: /: нолик$/ });

/** Клетка по номерам строки и столбца, считая с единицы (как в aria-label). */
export const cell = (page: Page, row: number, col: number): Locator =>
  page.getByRole("button", {
    name: new RegExp(`^Строка ${row}, столбец ${col}:`),
  });

export async function fillCredentials(
  page: Page,
  login: string,
  password: string,
): Promise<void> {
  await page.getByLabel("Логин").fill(login);
  await page.getByLabel("Пароль").fill(password);
}

export async function register(
  page: Page,
  login = uniqueLogin(),
  password = PASSWORD,
): Promise<string> {
  await page.goto("/");
  await page.getByRole("button", { name: "Регистрация", exact: true }).click();
  await fillCredentials(page, login, password);
  await page.getByRole("button", { name: "Зарегистрироваться" }).click();
  await expect(
    page.getByRole("button", { name: "Играть с компьютером" }),
  ).toBeVisible();
  return login;
}

export async function logout(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
}

export async function startGame(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Играть с компьютером" }).click();
  await expect(status(page)).toHaveText("Ваш ход");
}

/** Ход игрока и ответ компьютера (или конец партии). */
export async function playMove(
  page: Page,
  row: number,
  col: number,
): Promise<void> {
  const before = await crosses(page).count();
  await cell(page, row, col).click();
  // Свой ход рисуется сразу, не дожидаясь ответа сервера.
  await expect(crosses(page)).toHaveCount(before + 1);
  // «Компьютер отвечает…» сюда не подходит: ждём, пока ход вернётся к игроку
  // или партия закончится.
  await expect(status(page)).toHaveText(FINISHED_OR_MY_TURN);
}

export const FINISHED = /^(Ничья|Победил компьютер|Вы победили!)$/;
const FINISHED_OR_MY_TURN = /^(Ваш ход|Ничья|Победил компьютер|Вы победили!)$/;

/** Ходит в первую свободную клетку, пока партия не закончится. */
export async function playUntilFinished(page: Page): Promise<string> {
  // У игрока максимум пять ходов (X ходит первым, клеток девять).
  for (let move = 0; move < 5; move++) {
    const before = await crosses(page).count();
    await page.locator("button.cell:enabled").first().click();
    await expect(crosses(page)).toHaveCount(before + 1);
    await expect(status(page)).toHaveText(FINISHED_OR_MY_TURN);

    const text = await status(page).innerText();
    if (FINISHED.test(text)) return text;
  }
  throw new Error("Партия не закончилась за пять ходов игрока");
}

import { expect, test } from "@playwright/test";
import {
  PASSWORD,
  cell,
  fillCredentials,
  logout,
  register,
  status,
  uniqueLogin,
} from "./helpers.ts";

test.describe("регистрация и вход", () => {
  test("новый пользователь попадает на экран игры", async ({ page }) => {
    const login = await register(page);

    await expect(page.getByText(login, { exact: true })).toBeVisible();
    await expect(status(page)).toHaveText("Начните партию");
    // Пока партии нет, доска пустая и недоступна для ходов.
    await expect(cell(page, 2, 2)).toBeDisabled();
    await expect(page.getByRole("button", { name: /: пусто$/ })).toHaveCount(9);
  });

  test("после выхода можно войти снова теми же данными", async ({ page }) => {
    const login = await register(page);
    await logout(page);

    await fillCredentials(page, login, PASSWORD);
    await page.getByRole("button", { name: "Войти" }).click();

    await expect(
      page.getByRole("button", { name: "Играть с компьютером" }),
    ).toBeVisible();
    await expect(page.getByText(login, { exact: true })).toBeVisible();
  });

  test("неверный пароль показывает ошибку и не пускает", async ({ page }) => {
    const login = await register(page);
    await logout(page);

    await fillCredentials(page, login, "wrong-password");
    await page.getByRole("button", { name: "Войти" }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "Неверный логин или пароль.",
    );
    await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
  });

  test("несуществующий логин отвечает так же, как неверный пароль", async ({
    page,
  }) => {
    await page.goto("/");

    await fillCredentials(page, uniqueLogin("nobody"), PASSWORD);
    await page.getByRole("button", { name: "Войти" }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "Неверный логин или пароль.",
    );
  });

  test("повторная регистрация занятого логина отклоняется", async ({
    page,
  }) => {
    const login = await register(page);
    await logout(page);

    await page
      .getByRole("button", { name: "Регистрация", exact: true })
      .click();
    await fillCredentials(page, login, PASSWORD);
    await page.getByRole("button", { name: "Зарегистрироваться" }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "Этот логин уже занят. Выберите другой.",
    );
  });

  test("форма проверяет длину логина и пароля до отправки", async ({
    page,
  }) => {
    await page.goto("/");
    await page
      .getByRole("button", { name: "Регистрация", exact: true })
      .click();

    await fillCredentials(page, "ab", PASSWORD);
    await page.getByRole("button", { name: "Зарегистрироваться" }).click();
    await expect(page.getByRole("alert")).toHaveText(
      "Логин — минимум 3 символа.",
    );

    await fillCredentials(page, "abc", "12345");
    await page.getByRole("button", { name: "Зарегистрироваться" }).click();
    await expect(page.getByRole("alert")).toHaveText(
      "Пароль — минимум 6 символов.",
    );
  });

  test("при входе пустые поля не отправляются", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Войти" }).click();

    await expect(page.getByRole("alert")).toHaveText("Введите логин и пароль.");
  });

  test("перебор пароля блокируется ответом 429", async ({ page }) => {
    const login = await register(page);
    await logout(page);

    // Лимит по умолчанию — пять попыток; берём с запасом.
    let blocked = false;
    for (let attempt = 0; attempt < 8 && !blocked; attempt++) {
      await fillCredentials(page, login, `wrong-${attempt}`);
      const [response] = await Promise.all([
        page.waitForResponse((r) => r.url().endsWith("/auth/login")),
        page.getByRole("button", { name: "Войти" }).click(),
      ]);
      await expect(page.getByRole("button", { name: "Войти" })).toBeEnabled();
      blocked = response.status() === 429;
    }

    expect(blocked).toBe(true);
    await expect(page.getByRole("alert")).toContainText(
      "Слишком много неудачных попыток входа.",
    );
  });
});

test.describe("сессия", () => {
  test("после перезагрузки пользователь остаётся в системе", async ({
    page,
  }) => {
    const login = await register(page);

    await page.reload();

    await expect(page.getByText(login, { exact: true })).toBeVisible();
  });

  test("просроченный accessToken продлевается незаметно", async ({ page }) => {
    const login = await register(page);

    await page.evaluate(() => localStorage.setItem("ttt.access", "garbage"));
    await page.reload();

    await expect(page.getByText(login, { exact: true })).toBeVisible();
    // Продление выдало новую пару токенов.
    const access = await page.evaluate(() =>
      localStorage.getItem("ttt.access"),
    );
    expect(access).not.toBe("garbage");
  });

  test("негодные токены возвращают на форму входа", async ({ page }) => {
    await register(page);

    await page.evaluate(() => {
      localStorage.setItem("ttt.access", "garbage");
      localStorage.setItem("ttt.refresh", "garbage");
    });
    await page.reload();

    await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Играть с компьютером" }),
    ).toHaveCount(0);
  });
});

# 🤝 Руководство по вкладу в проект

Добро пожаловать! Здесь описано, как внести изменения в проект и не нарушить рабочие процессы.

---

## 🔁 Работа через Pull Request

✅ Все изменения вносятся **только через Pull Request**.  
🔄 Каждый PR должен проходить **линтинг** и **тесты**.  
🚫 Не комить в `main` напрямую!

---


## 🧼 Линтинг

### 🔹 Python (PEP8)

**Проверка качества кода:**

```bash
flake8 API/
flake8 backend/
flake8 ml_model/
```

**Автоматическое исправление:**

```bash
autopep8 путь/к/файлу.py --in-place --aggressive --aggressive
```

> Повтори `flake8` после `autopep8`, чтобы убедиться, что ошибок не осталось.

---

### 🔸 Frontend

> Убедись, что ESLint настроен.

```bash
npm run lint
```

---

## 🧪 Тестирование

### Python

Запуск всех тестов:

```bash
pytest
```

Запуск отдельных:

```bash
pytest test/test_backend.py
pytest test/test_parsing.py
pytest test/test_wildbox_client.py
pytest test/test_recomendation.py
```

### Frontend

```bash
npm run test
```



## ⚙️ CI/CD Workflows

При каждом `push` или `pull_request` запускаются автоматические проверки:

| Папка       | Проверки                                             |
|-------------|------------------------------------------------------|
| `ml_model/` | `flake8` + `pytest test/test_recomendation.py`      |
| `API/`      | `flake8` + `pytest test_parsing`, `test_wildbox`    |
| `backend/`  | `flake8` + `pytest test/test_backend.py`            |
| `frontend/` | `npm run lint` + `npm run test`                     |

---

## 🚀 Как создать Pull Request

```bash
git checkout -b feature/название-фичи
# Вносим изменения
git add .
git commit -m "feat: краткое описание"
git push origin feature/название-фичи
```

После пуша — создай PR в GitHub в ветку `main`.

---

## 💬 Вопросы?

Обращайся к мейнтейнеру или открывай issue.

# API Documentation for Remote Server

## General Information

**Title:** API удаленного сервера\
**Version:** 1.0.0

### Base URL

`https://virtserver.swaggerhub.com/FOKINKIR96_1/presentsimple_api/1.0.0`

---

## Endpoints

### 1. `/auth/send-confirmation-code`

#### POST: Send Confirmation Code to Email

**Description:** Отправить код подтверждения на email.

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Responses:**

- **200**: Успешная отправка кода подтверждения
  ```json
  {
    "success": true,
    "data": {
      "user_id": "12345"
    }
  }
  ```
- **400**: Неверный запрос
  ```json
  {
    "success": false,
    "message": "Некорректный email"
  }
  ```
- **404**: Пользователь не найден
  ```json
  {
    "success": false,
    "message": "Нет такого пользователя"
  }
  ```

---

### 2. `/auth/confirm-code`

#### POST: Confirm Confirmation Code

**Description:** Подтверждение кода подтверждения.

**Request Body:**

```json
{
  "user_id": "12345",
  "code": "67890"
}
```

**Responses:**

- **200**: Код успешно подтвержден
  ```json
  {
    "success": true
  }
  ```
- **400**: Неверный код подтверждения
  ```json
  {
    "success": false,
    "message": "Неверный код подтверждения"
  }
  ```
- **404**: Пользователь не найден
  ```json
  {
    "success": false,
    "message": "Пользователь не найден"
  }
  ```

---

### 3. `/auth/login`

#### POST: User Login

**Description:** Авторизация и сохранение данных пользователя.

**Request Body:**

```json
{
  "user_id": "12345",
  "chat_id": "54321"
}
```

**Responses:**

- **200**: Данные успешно сохранены
  ```json
  {
    "success": true
  }
  ```
- **400**: Неверные данные запроса
  ```json
  {
    "success": false,
    "message": "Неверные данные запроса"
  }
  ```

---

### 4. `/auth/logout`

#### POST: User Logout

**Description:** Выход из аккаунта.

**Request Body:**

```json
{
  "user_id": "12345"
}
```

**Responses:**

- **200**: Успешный выход из аккаунта
  ```json
  {
    "success": true
  }
  ```
- **404**: Пользователь не найден
  ```json
  {
    "success": false,
    "message": "Пользователь не найден"
  }
  ```

---

### 5. `/users/available-filters`

#### GET: Get Available Filters for Users

**Description:** Получение доступных полей для фильтрации пользователей.

**Responses:**

- **200**: Список полей для фильтрации
  ```json
  {
    "data": [
      {
        "group_label": "Базовая информация",
        "fields": [
          {
            "name": "age",
            "label": "Возраст",
            "type": "number"
          }
        ]
      }
    ]
  }
  ```
- **500**: Внутренняя ошибка сервера
  ```json
  {
    "success": false,
    "message": "Внутренняя ошибка сервера"
  }
  ```

---

### 6. `/users/filter`

#### POST: Get Users with Filters and Pagination

**Description:** Получение списка пользователей с фильтрацией и пагинацией.

**Query Parameters:**

- `page` (integer, default: 1): Номер страницы.
- `limit` (integer, default: 10): Лимит пользователей на странице.

**Request Body:**

```json
{
  "additionalProperties": "string"
}
```

**Responses:**

- **200**: Список пользователей
  ```json
  {
    "success": true,
    "count": 100,
    "next_page": "/users/filter?page=2&limit=10",
    "prev_page": null,
    "data": [
      {
        "user_id": "12345",
        "chat_id": "54321"
      }
    ]
  }
  ```
- **400**: Неверные параметры запроса
  ```json
  {
    "success": false,
    "message": "Неверные параметры запроса"
  }
  ```
- **500**: Внутренняя ошибка сервера
  ```json
  {
    "success": false,
    "message": "Внутренняя ошибка сервера"
  }
  ```



----------


Вот варианты типов полей:  


5 `date`  
Поле даты с ограничениями:  
{
    "name": "birth_date",
    "label": "Дата рождения",
    "type": "date",
    "min_date": "1900-01-01",
    "max_date": "2023-12-31"
}

6 `date_range`  
Диапазон дат ( а можно использовать два `date`):  
{
    "name": "hire_date_range",
    "label": "Дата найма",
    "type": "date_range",
    "min_date": "2020-01-01",
    "max_date": "2023-12-31"
}

7 `multiple_choice`  
Выбор нескольких значений:  
{
    "name": "tags",
    "label": "Теги",
    "type": "multiple_choice",
    "choices": ["Python", "JavaScript", "Go", "Rust"]
}

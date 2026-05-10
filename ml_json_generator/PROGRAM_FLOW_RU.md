# Как работает программа

Это простое описание всего пути: от человеческого запроса до JSON, таблиц, датасета и макроса КОМПАС.

## 1. Что вводит человек

Есть два режима.

Первый режим: полный запрос.

```text
Сделай скворечник с корпусом, крышей, отверстием и жердочкой.
```

Модель должна сразу вернуть весь JSON-план.

Второй режим: пошаговое редактирование.

```text
Шаг 1: создай корпус.
Шаг 2: к текущему JSON добавь крышу.
Шаг 3: к текущему JSON добавь отверстие.
Шаг 4: к текущему JSON добавь жердочку.
```

Модель каждый раз получает текущий JSON и маленькую инструкцию. Это основной новый режим.

Третий режим: автоматический планировщик.

```text
Большой запрос пользователя
-> планировщик разбивает его на шаги
-> incremental-режим выполняет шаги один за другим
-> на каждом шаге модель получает текущий JSON и следующую инструкцию
```

Пример:

```text
Сделай скворечник с крышей, дыркой и жердочкой.
```

Планировщик превращает это в:

```text
1. Создай прямоугольный корпус.
2. Добавь треугольную крышу сверху.
3. Добавь круглое отверстие на передней стороне.
4. Добавь цилиндрическую жердочку под отверстием.
```

Потом эти шаги выполняются по очереди.

## 2. Что получает модель

В полном режиме модель получает только задачу.

```text
User request -> model -> full JSON
```

В пошаговом режиме модель получает текущий план и инструкцию.

```text
Current JSON + instruction -> model -> updated full JSON
```

Важно: модель возвращает не кусок JSON, а полный обновленный JSON целиком.

В режиме планировщика модель запускается минимум два типа раз:

```text
1. Planner-model call:
   user request -> list of steps

2. Builder-model calls:
   current JSON + step instruction -> updated JSON
```

Количество builder-запусков зависит от числа шагов и ошибок. Если шаг получился с первой попытки, лишние попытки не запускаются.

## 3. Что такое JSON-план

JSON-план - это промежуточный язык между человеком и КОМПАС.

Пример:

```json
{
  "version": "0.1",
  "units": "mm",
  "part_name": "simple_house",
  "commands": [
    {
      "id": "body",
      "type": "create_box",
      "size": [80, 50, 40],
      "placement": {"origin": [0, 0, 0]}
    },
    {
      "id": "roof",
      "type": "create_triangle",
      "size": [80, 25, 40],
      "attach": {
        "target": "body",
        "face": "top",
        "position": "center"
      }
    }
  ]
}
```

Модель не пишет макрос напрямую. Она пишет только JSON-команды.

## 4. Какие команды разрешены

Сейчас разрешены базовые CAD-примитивы:

```text
create_box
cut_box
create_prism
cut_prism
create_triangle
cut_triangle
create_cylinder
cut_cylinder
```

Нельзя писать специальные команды вроде:

```text
create_birdhouse
create_table
create_plate_with_holes
```

Такие объекты должны собираться из базовых команд.

## 5. Что делает валидатор

После ответа модели программа проверяет JSON.

Проверяется:

```text
JSON читается
version == "0.1"
units == "mm"
part_name есть
commands есть
типы команд разрешены
размеры положительные
id не повторяются
attach.target существует
геометрические поля имеют правильный формат
```

В пошаговом режиме есть дополнительная проверка:

```text
старые команды не должны исчезать
старые команды не должны менять тип
новый JSON должен сохранить уже построенную деталь
```

## 6. Что делает placement_resolver

Модель может писать удобные высокоуровневые команды:

```json
"attach": {
  "target": "body",
  "face": "top",
  "position": "center"
}
```

Но макросу нужны конкретные координаты. Поэтому `placement_resolver.py` переводит `attach` и `placement` в низкоуровневые поля:

```text
origin
points
center
plane
extrude
select_point
```

То есть модель думает человечески, а resolver приводит JSON к виду, который умеет генератор макросов.

## 7. Что происходит при ошибке

Если ответ неправильный, программа не выбрасывает его.

Она сохраняет:

```text
запрос
шаг
номер попытки
сырой ответ модели
ошибку
описание ошибки
```

Это нужно, чтобы потом разбирать, на чем модель ломается.

## 8. Новый принцип попыток

Раньше программа всегда генерировала несколько кандидатов.

Теперь в incremental-режиме логика такая:

```text
попытка 1
если правильно -> сохранить и перейти к следующему шагу
если ошибка -> сохранить ошибку и попробовать еще раз

максимум 8 попыток
```

Пример:

```text
попытка 1: ошибка
попытка 2: ошибка
попытка 3: правильно
попытки 4-8 не делаются
```

Это экономит время и не плодит лишние ответы.

В режиме планировщика это работает так:

```text
1 запрос пользователя
-> 1 запуск планировщика
-> N шагов
-> на каждом шаге до 8 попыток
-> первый валидный ответ завершает шаг
-> если все шаги завершены, задача выполнена
```

То есть программа сама решает, сколько шагов нужно, а потом выполняет их последовательно.

## 9. Куда пишутся логи

Старые batch-таблицы остаются в:

```text
ml_json_generator/logs/
```

Новый incremental-режим создает отдельную папку на каждый запуск:

```text
ml_json_generator/logs/incremental_run_YYYYMMDD_HHMMSS/
```

Внутри:

```text
all_candidates.csv
accepted_candidates.csv
rejected_candidates.csv
step_summary.csv
task_summary.jsonl
tasks/
  inc_001_box_roof.csv
  inc_002_birdhouse.csv
```

Главная удобная таблица для разбора одной задачи лежит в `tasks/`.

## 10. Что лежит в таблице задачи

Одна строка - одна попытка модели на одном шаге.

Там есть:

```text
task_id
step_id
step_index
attempt_index
instruction
input_plan_json
raw_output
raw_plan_json
resolved_plan_json
verdict
accepted
error_stage
error_message
error_description
score
```

Это формат:

```text
запрос -> ответ -> ошибка или успех
```

## 11. Как получается макрос

Когда JSON прошел проверку:

```text
JSON
-> resolve_placements()
-> validate_plan()
-> write_macro()
-> .m3m macro
```

Файл макроса сохраняется в папку с результатами.

## 12. Как получается датасет для обучения

Успешные ответы можно превратить в обучающие пары.

Для полного режима:

```text
user request -> final JSON
```

Для incremental-режима:

```text
current JSON + instruction -> updated JSON
```

Второй формат лучше для обучения, потому что задача модели становится меньше и точнее.

## 13. Как запустить новый режим

В Colab открой `colab_json_repair_loop.ipynb`.

Для быстрой проверки:

```python
INCREMENTAL_LIMIT = 2
INCREMENTAL_ATTEMPTS = 3
```

Для полного запуска:

```python
INCREMENTAL_LIMIT = None
INCREMENTAL_ATTEMPTS = 8
```

Запускается:

```python
incremental_result = run_incremental_tasks(
    INCREMENTAL_TASKS_PATH,
    limit=INCREMENTAL_LIMIT,
    attempt_limit=INCREMENTAL_ATTEMPTS,
)
```

## 14. Как запустить режим планировщика

Этот режим принимает один большой запрос и сам разбивает его на шаги.

```python
planned_result = run_planned_incremental_request(
    user_request="Make a birdhouse with a rectangular body, triangular roof, round front entrance hole, and a small cylindrical perch.",
    part_name="planned_birdhouse_demo",
    task_id="planned_001_birdhouse",
    max_steps=6,
    attempt_limit=3,
)
```

Для серьезного запуска можно поставить:

```python
max_steps=8
attempt_limit=8
```

Результаты пишутся в отдельную папку:

```text
logs/planned_incremental_run_YYYYMMDD_HHMMSS/
```

Внутри есть:

```text
planned_task.json          - как программа разбила запрос на шаги
planned_tasks.jsonl        - журнал планировщика
all_candidates.csv         - все попытки построения
accepted_candidates.csv    - успешные шаги
rejected_candidates.csv    - ошибки
step_summary.csv           - итог по каждому шагу
task_summary.jsonl         - итог по задаче
tasks/<task_id>.csv        - подробная таблица конкретной задачи
```

## 15. Что сейчас важно оценить

Нужно смотреть не только `accepted`, но и причины ошибок.

Если много ошибок вида:

```text
attach.face not supported
attach.position currently supports only center
placed cylinder currently supports attach.face='front'
```

значит модель уже пытается выразить правильную идею, но наш JSON-язык или resolver пока слишком узкий.

Это не всегда проблема модели. Часто это подсказка, какую возможность нужно добавить в программу.

# HomeworksChecker

Автоматическая система проверки домашних заданий по C++.

## Быстрый старт

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/niklvdanya/HomeworksChecker.git
   cd HomeworksChecker
   ```

2. **Создайте папки для студентов**
   ```bash
   mkdir student1 student2 student3
   ```

3. **Добавьте домашние задания студентов**
   
   Структура должна быть такой:
   ```
   HomeworksChecker/
   ├── student1/
   │   └── HomeAssignments/  # или HomeAssignment
   │       ├── Assignment3/
   │       └── Assignment4/
   ├── student2/
   │   └── HomeAssignments/
   │       ├── Assignment3/
   │       └── Assignment4/
   └── ...
   ```

4. **Запустите проверку**
   ```bash
   docker-compose up
   ```

## Результаты

После выполнения отчеты будут сохранены в папке `reports/`:
- `summary_report.txt` - сводный отчет по всем студентам
- `student1_report.txt`, `student2_report.txt` - детальные отчеты по каждому студенту

## Настройка системы оценивания

Все штрафы и параметры можно настроить в файле `check_homework.py` в разделе констант:

```python
# Штрафы за различные нарушения
PENALTY_NO_MAKEFILE = 10            # Makefile отсутствует
PENALTY_BUILD_FAILED = 15           # Проект не собирается
PENALTY_NO_TESTS = 10               # Тесты отсутствуют
PENALTY_MEMORY_LEAKS_DEFINITE = 3   # Утечки памяти
# ... и другие
```

## Что проверяется

- ✅ Наличие и корректность Makefile
- ✅ Сборка проекта (`make`)
- ✅ Наличие и выполнение тестов
- ✅ Стиль кода (astyle)
- ✅ Статический анализ (cppcheck, clang-tidy)
- ✅ Утечки памяти (valgrind)
- ✅ Специфичные требования для Assignment3/Assignment4

## Названия папок студентов

Система ищет папки, начинающиеся с `student`:
- `student1`, `student2`, `student_ivanov`, `studentA` - ✅

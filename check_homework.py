#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import tempfile
import signal
from datetime import datetime
from pathlib import Path

# =============================================================================
# КОНСТАНТЫ ДЛЯ НАСТРОЙКИ СИСТЕМЫ ОЦЕНИВАНИЯ
# =============================================================================

INITIAL_SCORE = 100
REPORTS_DIR = "/app/reports"
TIMEOUT_SECONDS = 30

# Пути к заданиям 
ASSIGNMENTS_TO_CHECK = ["Assignment3", "Assignment4"]

# Возможные названия папок с заданиями 
POSSIBLE_ASSIGNMENT_FOLDER_NAMES = [
    "HomeAssignmets", "HomeAssignments", "HomeAssignment", 
    "Assignments", "Assignment", "homework", "Homework"
]

# =============================================================================
# ШТРАФЫ ЗА РАЗЛИЧНЫЕ НАРУШЕНИЯ
# =============================================================================

# Критические ошибки
PENALTY_NO_ASSIGNMENTS_FOLDER = 50  # Папка с заданиями не найдена
PENALTY_NO_ASSIGNMENT_DIR = 20      # Конкретное задание отсутствует
PENALTY_BUILD_FAILED = 15           # Проект не собирается
PENALTY_NO_TESTS = 10               # Тесты отсутствуют
PENALTY_NO_INHERITANCE = 10         # Нет наследования классов (Assignment3)

# Серьезные ошибки
PENALTY_NO_MAKEFILE = 10            # Makefile отсутствует
PENALTY_NO_STREAM_OPERATOR = 8      # Оператор << не реализован (Assignment4)
PENALTY_NO_COMPARISON_OPERATORS = 8 # Операторы сравнения не реализованы (Assignment4)
PENALTY_REQUIRED_FLAGS_MISSING = 5  # Нет обязательных флагов (Assignment4)
PENALTY_TESTS_FAILED = 5            # Тесты не проходят
PENALTY_MAX_STYLE_PENALTY = 5       # Максимальный штраф за стиль

# Предупреждения
PENALTY_FEW_CLASS_FILES = 3         # Мало файлов классов (Assignment3)
PENALTY_NO_BASE_CLASS = 3           # Базовый класс не найден (Assignment3)
PENALTY_MEMORY_LEAKS_DEFINITE = 3   # Определенные утечки памяти
PENALTY_MAX_CLANG_TIDY = 3          # Максимальный штраф за clang-tidy
PENALTY_NO_COMPILER_VARS = 2        # Нет переменных компилятора в Makefile
PENALTY_NO_FLAGS_VARS = 2           # Нет переменных флагов в Makefile
PENALTY_MEMORY_ERRORS = 2           # Ошибки памяти
PENALTY_CPPCHECK_ISSUES = 2         # Предупреждения cppcheck

# Минимальные штрафы
PENALTY_MEMORY_LEAKS_POSSIBLE = 1   # Возможные утечки памяти
PENALTY_VALGRIND_TIMEOUT = 1        # Таймаут valgrind

# Требования для Assignment3
MIN_CLASS_FILES_ASSIGNMENT3 = 4     # Минимум файлов классов

# Оценочные границы
GRADE_EXCELLENT = 80    # Отлично
GRADE_GOOD = 60        # Хорошо  
GRADE_SATISFACTORY = 40 # Удовлетворительно

# =============================================================================
# ЦВЕТОВЫЕ КОНСТАНТЫ ДЛЯ ВЫВОДА
# =============================================================================

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# =============================================================================
# ОСНОВНОЙ КОД
# =============================================================================

def log(message):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{Colors.BLUE}[{timestamp}]{Colors.NC} {message}")

def error(message):
    """Вывод ошибки"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def warning(message):
    """Вывод предупреждения"""  
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def success(message):
    """Вывод успешного сообщения"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def find_assignments_folder(student_dir):
    """Поиск папки с заданиями"""
    student_path = Path(student_dir)
    
    # Проверяем известные названия папок
    for name in POSSIBLE_ASSIGNMENT_FOLDER_NAMES:
        folder_path = student_path / name
        if folder_path.is_dir():
            return str(folder_path)
    
    for item in student_path.iterdir():
        if item.is_dir() and "Assignment" in item.name:
            if any(char.isdigit() for char in item.name):
                return str(student_path)
            else:
                return str(item)
    
    return None

def run_command(command, cwd=None, timeout=None, input_text=None):
    """Запуск команды с обработкой ошибок"""
    try:
        if input_text:
            result = subprocess.run(
                command, shell=True, cwd=cwd, timeout=timeout,
                capture_output=True, text=True, input=input_text
            )
        else:
            result = subprocess.run(
                command, shell=True, cwd=cwd, timeout=timeout,
                capture_output=True, text=True
            )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout expired"
    except Exception as e:
        return 1, "", str(e)

def check_file_exists(directory, patterns):
    """Проверка существования файлов по паттернам"""
    dir_path = Path(directory)
    for pattern in patterns:
        if list(dir_path.glob(pattern)):
            return True
    return False

def count_files(directory, patterns):
    """Подсчет файлов по паттернам"""
    dir_path = Path(directory)
    count = 0
    for pattern in patterns:
        count += len(list(dir_path.glob(pattern)))
    return count

def search_in_files(directory, pattern, file_patterns):
    """Поиск паттерна в файлах"""
    dir_path = Path(directory)
    for file_pattern in file_patterns:
        for file_path in dir_path.rglob(file_pattern):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if pattern in content:
                        return True
            except:
                continue
    return False

def check_student(student_dir):
    """Основная функция проверки студента"""
    student_name = Path(student_dir).name
    total_score = INITIAL_SCORE
    
    log(f"Проверка студента: {student_name}")
    
    reports_path = Path(REPORTS_DIR)
    reports_path.mkdir(parents=True, exist_ok=True)
    
    report_file = reports_path / f"{student_name}_report.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"=== ОТЧЕТ ПО ПРОВЕРКЕ СТУДЕНТА: {student_name} ===\n")
        f.write(f"Начальный балл: {total_score}\n\n")
        
        assignments_base_dir = find_assignments_folder(student_dir)
        
        if not assignments_base_dir:
            error(f"Папка с заданиями не найдена у студента {student_name}")
            f.write("КРИТИЧЕСКАЯ ОШИБКА: Папка с заданиями не найдена\n")
            f.write("Структура директории студента:\n")
            
            for item in Path(student_dir).rglob("*"):
                if item.is_dir():
                    f.write(f"{item}\n")
                    
            total_score -= PENALTY_NO_ASSIGNMENTS_FOLDER
            f.write(f"=== ИТОГОВЫЙ БАЛЛ: {total_score}/{INITIAL_SCORE} ===\n")
            print(f"{student_name}: {total_score}/{INITIAL_SCORE}")
            return
        
        success(f"Найдена папка с заданиями: {assignments_base_dir}")
        f.write(f"Папка с заданиями: {assignments_base_dir}\n\n")
        
        # Проверка каждого задания
        for assignment in ASSIGNMENTS_TO_CHECK:
            assignment_dir = Path(assignments_base_dir) / assignment
            f.write(f"--- Проверка {assignment} ---\n")
            f.write(f"Путь: {assignment_dir}\n")
            
            if not assignment_dir.is_dir():
                error(f"Директория {assignment} не найдена у студента {student_name}")
                f.write(f"КРИТИЧЕСКАЯ ОШИБКА: Директория {assignment} отсутствует (-{PENALTY_NO_ASSIGNMENT_DIR} баллов)\n")
                f.write("Доступные папки в {}:\n".format(Path(assignments_base_dir).name))
                
                try:
                    for item in Path(assignments_base_dir).iterdir():
                        f.write(f"{item.name}\n")
                except:
                    f.write("Не удается прочитать содержимое\n")
                
                total_score -= PENALTY_NO_ASSIGNMENT_DIR
                continue
            
            original_dir = os.getcwd()
            os.chdir(assignment_dir)
            
            try:
                # Проверка Makefile
                if not (Path(".").glob("Makefile") or Path(".").glob("makefile")):
                    error(f"Makefile отсутствует в {assignment}")
                    f.write(f"ОШИБКА: Makefile отсутствует (-{PENALTY_NO_MAKEFILE} баллов)\n")
                    total_score -= PENALTY_NO_MAKEFILE
                else:
                    success("Makefile найден")
                    f.write("OK: Makefile присутствует\n")
                
                makefile_name = None
                if Path("Makefile").exists():
                    makefile_name = "Makefile"
                elif Path("makefile").exists():
                    makefile_name = "makefile"
                
                if makefile_name:
                    try:
                        with open(makefile_name, 'r') as mf:
                            makefile_content = mf.read()
                            
                        if not ("CC=" in makefile_content or "CXX=" in makefile_content):
                            warning("В Makefile не найдены переменные компилятора")
                            f.write(f"ПРЕДУПРЕЖДЕНИЕ: Нет переменных компилятора в Makefile (-{PENALTY_NO_COMPILER_VARS} балла)\n")
                            total_score -= PENALTY_NO_COMPILER_VARS
                        
                        if not any(flag in makefile_content for flag in ["CFLAGS", "CXXFLAGS", "CCXFLAGS"]):
                            warning("В Makefile не найдены переменные флагов")
                            f.write(f"ПРЕДУПРЕЖДЕНИЕ: Нет переменных флагов в Makefile (-{PENALTY_NO_FLAGS_VARS} балла)\n")
                            total_score -= PENALTY_NO_FLAGS_VARS
                        
                        # Специальная проверка для Assignment4
                        if assignment == "Assignment4":
                            required_flags = ["-Werror", "-Wpedantic", "-Wall"]
                            has_all_flags = all(flag in makefile_content for flag in required_flags)
                            
                            if not has_all_flags:
                                error("Отсутствуют обязательные флаги компилятора в Assignment4")
                                f.write(f"ОШИБКА: Нет флагов -Werror -Wpedantic -Wall в Assignment4 (-{PENALTY_REQUIRED_FLAGS_MISSING} баллов)\n")
                                total_score -= PENALTY_REQUIRED_FLAGS_MISSING
                            else:
                                success("Обязательные флаги -Werror -Wpedantic -Wall найдены в Makefile")
                                f.write("OK: Найдены обязательные флаги -Werror -Wpedantic -Wall\n")
                    except:
                        pass
                
                # Сборка проекта
                log("Попытка сборки проекта...")
                
                returncode, _, _ = run_command("make clean")
                if returncode == 0:
                    f.write("OK: make clean выполнен успешно\n")

                returncode, stdout, stderr = run_command("make")
                if returncode == 0:
                    success("Проект собирается успешно")
                    f.write("OK: Проект собирается\n")
                else:
                    error("Проект не собирается")
                    f.write(f"КРИТИЧЕСКАЯ ОШИБКА: Проект не собирается (-{PENALTY_BUILD_FAILED} баллов)\n")
                    f.write("Ошибки сборки:\n")
                    f.write(stderr[:1000] + "\n")  
                    total_score -= PENALTY_BUILD_FAILED
                    continue
                
                # Специфичные проверки для Assignment3
                if assignment == "Assignment3":
                    cpp_files = count_files(".", ["*.cpp", "*.hpp", "*.h"])
                    test_files = count_files(".", ["*test*", "*Test*", "*TEST*"])
                    cpp_files -= test_files
                    
                    f.write(f"Найдено файлов исходного кода: {cpp_files}\n")
                    
                    if cpp_files < MIN_CLASS_FILES_ASSIGNMENT3:
                        warning("Недостаточно файлов классов (ожидается минимум 4)")
                        f.write(f"ПРЕДУПРЕЖДЕНИЕ: Мало файлов классов (-{PENALTY_FEW_CLASS_FILES} балла)\n")
                        total_score -= PENALTY_FEW_CLASS_FILES
                    
                    base_class_patterns = ["class.*Transformer", "class.*Robot", "class.*Bot"]
                    has_base_class = False
                    for pattern in base_class_patterns:
                        if search_in_files(".", pattern, ["*.h", "*.hpp", "*.cpp"]):
                            has_base_class = True
                            break
                    
                    if not has_base_class:
                        warning("Не найден базовый класс с подходящим именем")
                        f.write(f"ПРЕДУПРЕЖДЕНИЕ: Базовый класс не найден (-{PENALTY_NO_BASE_CLASS} балла)\n")
                        total_score -= PENALTY_NO_BASE_CLASS
                    
                    inheritance_patterns = [": public", ": private", ": protected"]
                    has_inheritance = any(search_in_files(".", pattern, ["*.h", "*.hpp", "*.cpp"]) 
                                        for pattern in inheritance_patterns)
                    
                    if not has_inheritance:
                        error("Наследование не найдено")
                        f.write(f"ОШИБКА: Нет наследования классов (-{PENALTY_NO_INHERITANCE} баллов)\n")
                        total_score -= PENALTY_NO_INHERITANCE
                
                # Специфичные проверки для Assignment4
                if assignment == "Assignment4":
                    if search_in_files(".", "operator<<", ["*.h", "*.hpp", "*.cpp"]):
                        success(f"Оператор << найден в {assignment}")
                        f.write("OK: Оператор << реализован\n")
                    else:
                        error(f"Оператор << не найден в {assignment}")
                        f.write(f"ОШИБКА: Оператор << не реализован (-{PENALTY_NO_STREAM_OPERATOR} баллов)\n")
                        total_score -= PENALTY_NO_STREAM_OPERATOR

                    comparison_patterns = ["operator<", "operator>", "operator=", "operator!"]
                    has_comparison = any(search_in_files(".", pattern, ["*.h", "*.hpp", "*.cpp"]) 
                                       for pattern in comparison_patterns)
                    
                    if has_comparison:
                        success(f"Операторы сравнения найдены в {assignment}")
                        f.write("OK: Операторы сравнения реализованы\n")
                    else:
                        error(f"Операторы сравнения не найдены в {assignment}")
                        f.write(f"ОШИБКА: Операторы сравнения не реализованы (-{PENALTY_NO_COMPARISON_OPERATORS} баллов)\n")
                        total_score -= PENALTY_NO_COMPARISON_OPERATORS
                
                # Проверка тестов
                test_files = count_files(".", ["*test*.cpp", "*test*.hpp", "*test*.h", 
                                             "*Test*.cpp", "*Test*.hpp", "*Test*.h",
                                             "*TEST*.cpp", "*TEST*.hpp", "*TEST*.h"])
                
                if test_files == 0:
                    error("Тесты не найдены")
                    f.write(f"ОШИБКА: Тесты отсутствуют (-{PENALTY_NO_TESTS} баллов)\n")
                    total_score -= PENALTY_NO_TESTS
                else:
                    success(f"Тесты найдены ({test_files} файлов)")
                    f.write(f"OK: Найдено {test_files} файлов тестов\n")
                    
                    # Запуск тестов
                    log("Попытка запуска тестов через 'make test'...")
                    returncode, stdout, stderr = run_command("make test", timeout=TIMEOUT_SECONDS)
                    
                    if returncode == 0:
                        success("Тесты выполнены успешно")
                        f.write("OK: Тесты проходят (make test)\n")
                    else:
                        warning("Тесты завершились с ошибкой")
                        f.write(f"ПРЕДУПРЕЖДЕНИЕ: Тесты не проходят (-{PENALTY_TESTS_FAILED} баллов)\n")
                        f.write("Вывод тестов:\n")
                        f.write((stdout + stderr)[:500] + "\n")
                        total_score -= PENALTY_TESTS_FAILED
                
                # Проверка стиля с astyle
                log("Проверка стиля кода...")
                if subprocess.run(["which", "astyle"], capture_output=True).returncode == 0:
                    style_issues = 0
                    style_penalty = 0
                    
                    for file_path in Path(".").rglob("*.cpp"):
                        if file_path.is_file():
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as tmp:
                                tmp_name = tmp.name
                                subprocess.run(f"cp {file_path} {tmp_name}", shell=True)
                                
                            returncode, _, _ = run_command(f"astyle -A1 -s4 --quiet {tmp_name}")
                            
                            diff_result = subprocess.run(f"diff -q {file_path} {tmp_name}", 
                                                       shell=True, capture_output=True)
                            
                            if diff_result.returncode != 0:
                                style_issues += 1
                                style_penalty += 1
                            
                            os.unlink(tmp_name)
                    
                    if style_issues > 0:
                        final_penalty = min(style_penalty // 5, PENALTY_MAX_STYLE_PENALTY)
                        if final_penalty > 0:
                            warning(f"Найдены проблемы со стилем кода: {style_issues} файлов")
                            f.write(f"ПРЕДУПРЕЖДЕНИЕ: Проблемы со стилем кода (-{final_penalty} баллов)\n")
                            total_score -= final_penalty
                    else:
                        success("Стиль кода соответствует astyle")
                        f.write("OK: Стиль кода соответствует astyle (-A1 -s4)\n")
                else:
                    warning("astyle не установлен, пропускаем проверку стиля")
                    f.write("ПРЕДУПРЕЖДЕНИЕ: astyle не установлен, проверка стиля пропущена\n")
                
                # Статический анализ с cppcheck
                log("Статический анализ кода...")
                if subprocess.run(["which", "cppcheck"], capture_output=True).returncode == 0:
                    returncode, stdout, stderr = run_command(
                        "cppcheck --error-exitcode=1 --enable=warning,style,performance,portability .", 
                        timeout=TIMEOUT_SECONDS
                    )
                    
                    issues_output = stdout + stderr
                    cppcheck_issues = len([line for line in issues_output.split('\n') 
                                         if any(word in line for word in ['error', 'warning', 'style', 'performance', 'portability'])
                                         and 'Checking' not in line])
                    
                    if cppcheck_issues > 0:
                        warning(f"Найдены предупреждения статического анализа: {cppcheck_issues}")
                        f.write(f"ПРЕДУПРЕЖДЕНИЕ: Предупреждения cppcheck (-{PENALTY_CPPCHECK_ISSUES} балла)\n")
                        f.write(f"Детали cppcheck:\n{issues_output[:500]}\n")
                        total_score -= PENALTY_CPPCHECK_ISSUES
                    else:
                        success("Статический анализ пройден без предупреждений")
                        f.write("OK: Статический анализ cppcheck пройден\n")
                else:
                    warning("cppcheck не установлен, пропускаем статический анализ")
                    f.write("ПРЕДУПРЕЖДЕНИЕ: cppcheck не установлен, статический анализ пропущен\n")
                
                # Проверка clang-tidy
                log("Проверка clang-tidy...")
                if subprocess.run(["which", "clang-tidy"], capture_output=True).returncode == 0:
                    clang_tidy_issues = 0
                    
                    cpp_files = list(Path(".").glob("*.cpp"))[:5] 
                    
                    for cpp_file in cpp_files:
                        returncode, stdout, stderr = run_command(
                            f"clang-tidy {cpp_file} -- -std=c++17", 
                            timeout=TIMEOUT_SECONDS
                        )
                        
                        issues_output = stdout + stderr
                        if any(word in issues_output for word in ['warning:', 'error:']):
                            clang_tidy_issues += 1
                    
                    if clang_tidy_issues > 0:
                        penalty = min(clang_tidy_issues, PENALTY_MAX_CLANG_TIDY)
                        warning(f"Найдены предупреждения clang-tidy: {clang_tidy_issues} файлов")
                        f.write(f"ПРЕДУПРЕЖДЕНИЕ: Предупреждения clang-tidy (-{penalty} баллов)\n")
                        total_score -= penalty
                    else:
                        success("clang-tidy проверка пройдена без предупреждений")
                        f.write("OK: clang-tidy проверка пройдена\n")
                else:
                    warning("clang-tidy не установлен, пропускаем проверку")
                    f.write("ПРЕДУПРЕЖДЕНИЕ: clang-tidy не установлен, проверка пропущена\n")
                
                # Проверка утечек памяти с valgrind
                log("Проверка утечек памяти...")
                executable_files = []
                for item in Path(".").iterdir():
                    if item.is_file() and os.access(item, os.X_OK) and not item.suffix:
                        executable_files.append(str(item))
                
                executable_files = executable_files[:3]
                f.write(f"Найдены исполняемые файлы: {executable_files}\n")
                
                if not executable_files:
                    warning(f"Исполняемые файлы не найдены для проверки утечек памяти в {assignment}")
                    f.write("ПРЕДУПРЕЖДЕНИЕ: Исполняемые файлы не найдены, проверка утечек памяти пропущена\n")
                else:
                    if subprocess.run(["which", "valgrind"], capture_output=True).returncode == 0:
                        for exe in executable_files:
                            if Path(exe).is_file():
                                is_interactive = search_in_files(".", "std::cin", ["*.cpp"]) or \
                                               search_in_files(".", "Write your command", ["*.cpp"])
                                
                                if is_interactive:
                                    log(f"Обнаружен интерактивный ввод в {assignment}, использование команды 'off' для {exe}")
                                    returncode, stdout, stderr = run_command(
                                        f"valgrind --tool=memcheck --leak-check=full --error-exitcode=1 {exe}",
                                        timeout=TIMEOUT_SECONDS, input_text="off\n"
                                    )
                                else:
                                    returncode, stdout, stderr = run_command(
                                        f"valgrind --tool=memcheck --leak-check=full --error-exitcode=1 {exe}",
                                        timeout=TIMEOUT_SECONDS
                                    )
                                
                                valgrind_output = stdout + stderr
                                
                                if returncode == 124:  # Timeout
                                    warning(f"Исполняемый файл {exe} превысил таймаут valgrind в {assignment}")
                                    f.write(f"ПРЕДУПРЕЖДЕНИЕ: Исполняемый файл {Path(exe).name} превысил таймаут valgrind ({TIMEOUT_SECONDS} секунд) (-{PENALTY_VALGRIND_TIMEOUT} балл)\n")
                                    total_score -= PENALTY_VALGRIND_TIMEOUT
                                elif "definitely lost" in valgrind_output and any(char.isdigit() for char in valgrind_output.split("definitely lost")[1].split()[0] if "definitely lost" in valgrind_output):
                                    warning(f"Обнаружены утечки памяти (definitely lost) в {exe} в {assignment}")
                                    f.write(f"ПРЕДУПРЕЖДЕНИЕ: Утечки памяти (definitely lost) в {Path(exe).name} (-{PENALTY_MEMORY_LEAKS_DEFINITE} балла)\n")
                                    total_score -= PENALTY_MEMORY_LEAKS_DEFINITE
                                elif "possibly lost" in valgrind_output:
                                    warning(f"Обнаружены возможные утечки памяти (possibly lost) в {exe} в {assignment}")
                                    f.write(f"ПРЕДУПРЕЖДЕНИЕ: Возможные утечки памяти (possibly lost) в {Path(exe).name} (-{PENALTY_MEMORY_LEAKS_POSSIBLE} балл)\n")
                                    total_score -= PENALTY_MEMORY_LEAKS_POSSIBLE
                                elif "ERROR SUMMARY:" in valgrind_output and any(char.isdigit() and char != '0' for char in valgrind_output.split("ERROR SUMMARY:")[1].split()[0] if "ERROR SUMMARY:" in valgrind_output):
                                    warning(f"Обнаружены ошибки памяти в {exe} в {assignment}")
                                    f.write(f"ПРЕДУПРЕЖДЕНИЕ: Ошибки памяти в {Path(exe).name} (-{PENALTY_MEMORY_ERRORS} балла)\n")
                                    total_score -= PENALTY_MEMORY_ERRORS
                                else:
                                    success(f"Утечки памяти не обнаружены в {exe} в {assignment}")
                                    f.write(f"OK: Утечки памяти не обнаружены в {Path(exe).name}\n")
                    else:
                        warning(f"valgrind не установлен, пропускаем проверку утечек памяти в {assignment}")
                        f.write("ПРЕДУПРЕЖДЕНИЕ: valgrind не установлен, проверка утечек памяти пропущена\n")
                
            finally:
                os.chdir(original_dir)
            
            f.write("\n")
        
        # Итоговая оценка
        f.write(f"=== ИТОГОВЫЙ БАЛЛ: {total_score}/{INITIAL_SCORE} ===\n")
        
        if total_score >= GRADE_EXCELLENT:
            success(f"Студент {student_name}: {total_score}/{INITIAL_SCORE} баллов (Отлично)")
        elif total_score >= GRADE_GOOD:
            warning(f"Студент {student_name}: {total_score}/{INITIAL_SCORE} баллов (Хорошо)")
        elif total_score >= GRADE_SATISFACTORY:
            warning(f"Студент {student_name}: {total_score}/{INITIAL_SCORE} баллов (Удовлетворительно)")
        else:
            error(f"Студент {student_name}: {total_score}/{INITIAL_SCORE} баллов (Неудовлетворительно)")
        
        print(f"{student_name}: {total_score}/{INITIAL_SCORE}")
        return total_score

def main():
    """Основная функция"""
    log("Начало проверки домашних заданий")

    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    reports_path = Path(REPORTS_DIR)
    reports_path.mkdir(parents=True, exist_ok=True)
    
    summary_report = reports_path / "summary_report.txt"
    
    with open(summary_report, 'w', encoding='utf-8') as f:
        f.write("=== СВОДНЫЙ ОТЧЕТ ПО ВСЕМ СТУДЕНТАМ ===\n")
        f.write(f"Дата проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Рабочая директория: {os.getcwd()}\n")
        f.write(f"Проверяемые задания: {', '.join(ASSIGNMENTS_TO_CHECK)}\n")
        f.write("\n")
        
        total_students = 0
        passed_students = 0
        all_scores = []
        
        log("Поиск папок студентов...")
        student_dirs = []
        app_path = Path("/app")
        if app_path.exists():
            for item in app_path.iterdir():
                if item.is_dir() and item.name.startswith("student"):
                    student_dirs.append(item)
        
        student_dirs.sort(key=lambda x: x.name)
        
        for student_dir in student_dirs:
            student_name = student_dir.name
            log(f"Найден студент: {student_name}")
            total_students += 1
            
            try:
                score = check_student(str(student_dir))
                all_scores.append(score)
                
                f.write(f"{student_name}: {score} баллов\n")
                
                if score >= GRADE_SATISFACTORY:
                    passed_students += 1
                    
            except Exception as e:
                error(f"Ошибка при проверке студента {student_name}: {e}")
                f.write(f"{student_name}: ОШИБКА ПРОВЕРКИ\n")
                all_scores.append(0)
        
        f.write("\n")
        f.write("Общая статистика:\n")
        f.write(f"Всего студентов: {total_students}\n")
        f.write(f"Прошли (>={GRADE_SATISFACTORY} баллов): {passed_students}\n")
        
        if total_students > 0:
            success_rate = (passed_students * 100) // total_students
            f.write(f"Процент успешности: {success_rate}%\n")
            
            if all_scores:
                avg_score = sum(all_scores) // len(all_scores)
                f.write(f"Средний балл: {avg_score}\n")
                f.write(f"Максимальный балл: {max(all_scores)}\n")
                f.write(f"Минимальный балл: {min(all_scores)}\n")

        f.write("\nРаспределение оценок:\n")
        excellent = sum(1 for score in all_scores if score >= GRADE_EXCELLENT)
        good = sum(1 for score in all_scores if GRADE_GOOD <= score < GRADE_EXCELLENT)
        satisfactory = sum(1 for score in all_scores if GRADE_SATISFACTORY <= score < GRADE_GOOD)
        unsatisfactory = sum(1 for score in all_scores if score < GRADE_SATISFACTORY)
        
        f.write(f"Отлично (>={GRADE_EXCELLENT}): {excellent} студентов\n")
        f.write(f"Хорошо ({GRADE_GOOD}-{GRADE_EXCELLENT-1}): {good} студентов\n")
        f.write(f"Удовлетворительно ({GRADE_SATISFACTORY}-{GRADE_GOOD-1}): {satisfactory} студентов\n")
        f.write(f"Неудовлетворительно (<{GRADE_SATISFACTORY}): {unsatisfactory} студентов\n")
    
    log(f"Проверка завершена. Отчеты сохранены в {REPORTS_DIR}")
    success(f"Сводный отчет: {summary_report}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error("Проверка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        error(f"Критическая ошибка: {e}")
        sys.exit(1)
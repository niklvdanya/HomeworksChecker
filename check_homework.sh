#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' 


log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

find_assignments_folder() {
    local student_dir="$1"
    
    local possible_names=("HomeAssignmets" "HomeAssignments" "HomeAssignment" "Assignments" "Assignment" "homework" "Homework")
    
    for name in "${possible_names[@]}"; do
        if [ -d "${student_dir}/${name}" ]; then
            echo "${student_dir}/${name}"
            return 0
        fi
    done
    
    local found_dir=$(find "$student_dir" -maxdepth 2 -type d -name "*Assignment*" | head -1)
    if [ -n "$found_dir" ]; then
        if [[ "$found_dir" =~ Assignment[0-9] ]]; then
            echo "$(dirname "$found_dir")"
        else
            echo "$found_dir"
        fi
        return 0
    fi
    
    return 1
}

check_student() {
    local student_dir="$1"
    local student_name=$(basename "$student_dir")
    local total_score=100
    local report_dir="/app/reports"
    local report_file="${report_dir}/${student_name}_report.txt"
    
    log "Проверка студента: $student_name"
    
    mkdir -p "$report_dir"
    if [ ! -d "$report_dir" ]; then
        error "Не удалось создать директорию отчетов: $report_dir"
        return 1
    fi
    
    echo "=== ОТЧЕТ ПО ПРОВЕРКЕ СТУДЕНТА: $student_name ===" > "$report_file"
    echo "Начальный балл: $total_score" >> "$report_file"
    echo "" >> "$report_file"
    
    local assignments_base_dir
    assignments_base_dir=$(find_assignments_folder "$student_dir")
    
    if [ $? -ne 0 ] || [ -z "$assignments_base_dir" ]; then
        error "Папка с заданиями не найдена у студента $student_name"
        echo "КРИТИЧЕСКАЯ ОШИБКА: Папка с заданиями не найдена" >> "$report_file"
        echo "Структура директории студента:" >> "$report_file"
        find "$student_dir" -maxdepth 3 -type d | head -10 >> "$report_file"
        total_score=$((total_score - 50))
        echo "=== ИТОГОВЫЙ БАЛЛ: $total_score/100 ===" >> "$report_file"
        echo "$student_name: $total_score/100"
        return
    fi
    
    success "Найдена папка с заданиями: $assignments_base_dir"
    echo "Папка с заданиями: $assignments_base_dir" >> "$report_file"
    echo "" >> "$report_file"
    
    for assignment in Assignment3 Assignment4; do
        local assignment_dir="${assignments_base_dir}/${assignment}"
        echo "--- Проверка $assignment ---" >> "$report_file"
        echo "Путь: $assignment_dir" >> "$report_file"
        
        if [ ! -d "$assignment_dir" ]; then
            error "Директория $assignment не найдена у студента $student_name"
            echo "КРИТИЧЕСКАЯ ОШИБКА: Директория $assignment отсутствует (-20 баллов)" >> "$report_file"
            echo "Доступные папки в $(basename "$assignments_base_dir"):" >> "$report_file"
            ls -la "$assignments_base_dir" 2>/dev/null >> "$report_file" || echo "Не удается прочитать содержимое" >> "$report_file"
            total_score=$((total_score - 20))
            continue
        fi
        
        local original_dir=$(pwd)
        cd "$assignment_dir"
        
        if [ ! -f "Makefile" ] && [ ! -f "makefile" ]; then
            error "Makefile отсутствует в $assignment"
            echo "ОШИБКА: Makefile отсутствует (-10 баллов)" >> "$report_file"
            total_score=$((total_score - 10))
        else
            success "Makefile найден"
            echo "OK: Makefile присутствует" >> "$report_file"
        fi
        
        if [ -f "Makefile" ] || [ -f "makefile" ]; then
            makefile_name="Makefile"
            [ -f "makefile" ] && makefile_name="makefile"
            
            if ! grep -q "CC\s*=" "$makefile_name" && ! grep -q "CXX\s*=" "$makefile_name"; then
                warning "В Makefile не найдены переменные компилятора"
                echo "ПРЕДУПРЕЖДЕНИЕ: Нет переменных компилятора в Makefile (-2 балла)" >> "$report_file"
                total_score=$((total_score - 2))
            fi
            
            if ! grep -q "CFLAGS\|CXXFLAGS\|CCXFLAGS" "$makefile_name"; then
                warning "В Makefile не найдены переменные флагов"
                echo "ПРЕДУПРЕЖДЕНИЕ: Нет переменных флагов в Makefile (-2 балла)" >> "$report_file"
                total_score=$((total_score - 2))
            fi
            
            if [ "$assignment" = "Assignment4" ]; then
                if ! grep -q "\-Werror.*\-Wpedantic.*\-Wall\|\-Wall.*\-Werror.*\-Wpedantic\|\-Wpedantic.*\-Wall.*\-Werror" "$makefile_name"; then
                    error "Отсутствуют обязательные флаги компилятора в Assignment4"
                    echo "ОШИБКА: Нет флагов -Werror -Wpedantic -Wall в Assignment4 (-5 баллов)" >> "$report_file"
                    total_score=$((total_score - 5))
                else
                    success "Обязательные флаги -Werror -Wpedantic -Wall найдены в Makefile"
                    echo "OK: Найдены обязательные флаги -Werror -Wpedantic -Wall" >> "$report_file"
                fi
            fi
        fi
        
        log "Попытка сборки проекта..."
        if make clean 2>/dev/null; then
            echo "OK: make clean выполнен успешно" >> "$report_file"
        fi
        
        if make 2>/dev/null; then
            success "Проект собирается успешно"
            echo "OK: Проект собирается" >> "$report_file"
        else
            error "Проект не собирается"
            echo "КРИТИЧЕСКАЯ ОШИБКА: Проект не собирается (-15 баллов)" >> "$report_file"
            echo "Ошибки сборки:" >> "$report_file"
            make 2>&1 | head -10 >> "$report_file"
            total_score=$((total_score - 15))
            cd "$original_dir"
            continue
        fi
        
        if [ "$assignment" = "Assignment3" ]; then
            cpp_files=$(find . -name "*.cpp" -o -name "*.hpp" -o -name "*.h" | grep -v test | wc -l)
            echo "Найдено файлов исходного кода: $cpp_files" >> "$report_file"
            
            if [ $cpp_files -lt 4 ]; then
                warning "Недостаточно файлов классов (ожидается минимум 4)"
                echo "ПРЕДУПРЕЖДЕНИЕ: Мало файлов классов (-3 балла)" >> "$report_file"
                total_score=$((total_score - 3))
            fi
            
            if ! grep -r "class.*Transformer\|class.*Robot\|class.*Bot" . --include="*.h" --include="*.hpp" --include="*.cpp" > /dev/null; then
                warning "Не найден базовый класс с подходящим именем"
                echo "ПРЕДУПРЕЖДЕНИЕ: Базовый класс не найден (-3 балла)" >> "$report_file"
                total_score=$((total_score - 3))
            fi
            
            if ! grep -r ":\s*public\|:\s*private\|:\s*protected" . --include="*.h" --include="*.hpp" --include="*.cpp" > /dev/null; then
                error "Наследование не найдено"
                echo "ОШИБКА: Нет наследования классов (-10 баллов)" >> "$report_file"
                total_score=$((total_score - 10))
            fi
        fi
        
        if [ "$assignment" = "Assignment4" ]; then
            if grep -r "operator<<\|operator\s*<<" . --include="*.h" --include="*.hpp" --include="*.cpp" > /dev/null; then
                success "Оператор << найден в $assignment"
                echo "OK: Оператор << реализован" >> "$report_file"
            else
                error "Оператор << не найден в $assignment"
                echo "ОШИБКА: Оператор << не реализован (-8 баллов)" >> "$report_file"
                total_score=$((total_score - 8))
            fi
            
            if grep -r "operator[<>=!]" . --include="*.h" --include="*.hpp" --include="*.cpp" > /dev/null; then
                success "Операторы сравнения найдены в $assignment"
                echo "OK: Операторы сравнения реализованы" >> "$report_file"
            else
                error "Операторы сравнения не найдены в $assignment"
                echo "ОШИБКА: Операторы сравнения не реализованы (-8 баллов)" >> "$report_file"
                total_score=$((total_score - 8))
            fi
        fi
        
        test_files=$(find . -name "*test*" -o -name "*Test*" -o -name "*TEST*" | grep -E "\.(cpp|hpp|h)$" | wc -l)
        if [ $test_files -eq 0 ]; then
            error "Тесты не найдены"
            echo "ОШИБКА: Тесты отсутствуют (-10 баллов)" >> "$report_file"
            total_score=$((total_score - 10))
        else
            success "Тесты найдены ($test_files файлов)"
            echo "OK: Найдено $test_files файлов тестов" >> "$report_file"
            
            log "Попытка запуска тестов через 'make test'..."
            if make test > test_output.txt 2>&1; then
                success "Тесты выполнены успешно"
                echo "OK: Тесты проходят (make test)" >> "$report_file"
            else
                warning "Тесты завершились с ошибкой"
                echo "ПРЕДУПРЕЖДЕНИЕ: Тесты не проходят (-5 баллов)" >> "$report_file"
                echo "Вывод тестов:" >> "$report_file"
                cat test_output.txt | head -10 >> "$report_file" 2>/dev/null
                total_score=$((total_score - 5))
            fi
        fi
        
        log "Проверка стиля кода..."
        style_issues=0
        style_penalty=0
        style_details=""
        
        for file in $(find . -name "*.cpp" -o -name "*.h" -o -name "*.hpp"); do
            if command -v astyle >/dev/null 2>&1; then
                formatted_output=$(mktemp)
                cp "$file" "$formatted_output"
                astyle -A1 -s4 --quiet "$formatted_output"
                if ! diff -q "$file" "$formatted_output" >/dev/null 2>&1; then
                    style_issues=$((style_issues + 1))
                    diff_output=$(diff -u "$file" "$formatted_output" | head -10)
                    if echo "$diff_output" | grep -qE "^[+-][[:space:]]*$|^[+-]//|^[+-]/\*|^[+-][[:space:]]*[,;{}]"; then
                        style_details="$style_details\nФайл $file имеет незначительные проблемы форматирования (пробелы, отступы, комментарии):\n$diff_output\n"
                        style_penalty=$((style_penalty + 1))
                    else
                        style_details="$style_details\nФайл $file имеет проблемы форматирования (структура, порядок):\n$diff_output\n"
                        style_penalty=$((style_penalty + 5)) 
                    fi
                fi
                rm -f "$formatted_output"
            else
                warning "astyle не установлен, пропускаем проверку стиля"
                echo "ПРЕДУПРЕЖДЕНИЕ: astyle не установлен, проверка стиля пропущена" >> "$report_file"
            fi
        done
        
        if [ $style_issues -gt 0 ]; then
            final_penalty=$((style_penalty / 5))
            if [ $final_penalty -gt 5 ]; then
                final_penalty=5
            fi
            warning "Найдены проблемы со стилем кода: $style_issues файлов"
            echo "ПРЕДУПРЕЖДЕНИЕ: Проблемы со стилем кода (-${final_penalty} баллов)" >> "$report_file"
            echo -e "Детали проблем со стилем:\n$style_details" >> "$report_file"
            total_score=$((total_score - final_penalty))
        else
            success "Стиль кода соответствует astyle"
            echo "OK: Стиль кода соответствует astyle (-A1 -s4)" >> "$report_file"
        fi
        
        log "Статический анализ кода..."
        if command -v cppcheck >/dev/null 2>&1; then
            cppcheck_output=$(cppcheck --error-exitcode=1 --enable=warning,style,performance,portability . 2>&1 | grep -E "error|warning|style|performance|portability" | head -10)
            cppcheck_issues=$(echo -n "$cppcheck_output" | grep -v "Checking" | wc -l)
            if [ $cppcheck_issues -gt 0 ]; then
                warning "Найдены предупреждения статического анализа: $cppcheck_issues"
                echo "ПРЕДУПРЕЖДЕНИЕ: Предупреждения cppcheck (-2 балла)" >> "$report_file"
                echo "Детали cppcheck:\n$cppcheck_output" >> "$report_file"
                total_score=$((total_score - 2))
            else
                success "Статический анализ пройден без предупреждений"
                echo "OK: Статический анализ cppcheck пройден" >> "$report_file"
            fi
        else
            warning "cppcheck не установлен, пропускаем статический анализ"
            echo "ПРЕДУПРЕЖДЕНИЕ: cppcheck не установлен, статический анализ пропущен" >> "$report_file"
        fi
                log "Проверка clang-tidy..."
        if command -v clang-tidy >/dev/null 2>&1; then
            clang_tidy_issues=0
            clang_tidy_details=""

            cpp_files=$(find . -name "*.cpp" | head -5)  
            
            if [ -n "$cpp_files" ]; then
                for cpp_file in $cpp_files; do
                    clang_tidy_output=$(clang-tidy "$cpp_file" -- -std=c++17 2>&1 | grep -E "warning:|error:" | head -10)
                    
                    if [ -n "$clang_tidy_output" ]; then
                        clang_tidy_issues=$((clang_tidy_issues + 1))
                        clang_tidy_details="$clang_tidy_details\nФайл $cpp_file:\n$clang_tidy_output\n"
                    fi
                done
                
                if [ $clang_tidy_issues -gt 0 ]; then
                    penalty=$clang_tidy_issues
                    if [ $penalty -gt 3 ]; then
                        penalty=3
                    fi
                    
                    warning "Найдены предупреждения clang-tidy: $clang_tidy_issues файлов"
                    echo "ПРЕДУПРЕЖДЕНИЕ: Предупреждения clang-tidy (-${penalty} баллов)" >> "$report_file"
                    echo -e "Детали clang-tidy:$clang_tidy_details" >> "$report_file"
                    total_score=$((total_score - penalty))
                else
                    success "clang-tidy проверка пройдена без предупреждений"
                    echo "OK: clang-tidy проверка пройдена" >> "$report_file"
                fi
            else
                warning "Не найдены .cpp файлы для проверки clang-tidy"
                echo "ПРЕДУПРЕЖДЕНИЕ: Нет .cpp файлов для clang-tidy" >> "$report_file"
            fi
        else
            warning "clang-tidy не установлен, пропускаем проверку"
            echo "ПРЕДУПРЕЖДЕНИЕ: clang-tidy не установлен, проверка пропущена" >> "$report_file"
        fi

        log "Проверка утечек памяти..."
        executable_files=$(find . -executable -type f ! -name "*.sh" | head -3)
        echo "Найдены исполняемые файлы: $executable_files" >> "$report_file"
        if [ -z "$executable_files" ]; then
            warning "Исполняемые файлы не найдены для проверки утечек памяти в $assignment"
            echo "ПРЕДУПРЕЖДЕНИЕ: Исполняемые файлы не найдены, проверка утечек памяти пропущена" >> "$report_file"
        else
            for exe in $executable_files; do
                if [ -f "$exe" ]; then
                    if command -v valgrind >/dev/null 2>&1; then
                        is_interactive=0
                        if grep -r "std::cin\|cin\s*>>" . --include="*.cpp" > /dev/null || grep -r "Write your command" . --include="*.cpp" > /dev/null; then
                            is_interactive=1
                            log "Обнаружен интерактивный ввод в $assignment, использование команды 'off' для $exe"
                        fi
                        
                        if [ $is_interactive -eq 1 ]; then
                            valgrind_output=$(echo "off" | timeout 30 valgrind --tool=memcheck --leak-check=full --error-exitcode=1 "$exe" 2>&1)
                        else
                            valgrind_output=$(timeout 30 valgrind --tool=memcheck --leak-check=full --error-exitcode=1 "$exe" 2>&1)
                        fi
                        
                        if [ $? -eq 124 ]; then
                            warning "Исполняемый файл $exe превысил таймаут valgrind в $assignment"
                            echo "ПРЕДУПРЕЖДЕНИЕ: Исполняемый файл $(basename "$exe") превысил таймаут valgrind (30 секунд) (-1 балл)" >> "$report_file"
                            echo "Детали valgrind:\n$valgrind_output" >> "$report_file"
                            total_score=$((total_score - 1))
                        elif echo "$valgrind_output" | grep -q "definitely lost.*[1-9]"; then
                            warning "Обнаружены утечки памяти (definitely lost) в $exe в $assignment"
                            echo "ПРЕДУПРЕЖДЕНИЕ: Утечки памяти (definitely lost) в $(basename "$exe") (-3 балла)" >> "$report_file"
                            echo "Детали valgrind:\n$valgrind_output" >> "$report_file"
                            total_score=$((total_score - 3))
                        elif echo "$valgrind_output" | grep -q "possibly lost.*[1-9]"; then
                            warning "Обнаружены возможные утечки памяти (possibly lost) в $exe в $assignment"
                            echo "ПРЕДУПРЕЖДЕНИЕ: Возможные утечки памяти (possibly lost) в $(basename "$exe") (-1 балл)" >> "$report_file"
                            echo "Детали valgrind:\n$valgrind_output" >> "$report_file"
                            total_score=$((total_score - 1))
                        elif echo "$valgrind_output" | grep -q "ERROR SUMMARY: [1-9]"; then
                            warning "Обнаружены ошибки памяти в $exe в $assignment"
                            echo "ПРЕДУПРЕЖДЕНИЕ: Ошибки памяти в $(basename "$exe") (-2 балла)" >> "$report_file"
                            echo "Детали valgrind:\n$valgrind_output" >> "$report_file"
                            total_score=$((total_score - 2))
                        else
                            success "Утечки памяти не обнаружены в $exe в $assignment"
                            echo "OK: Утечки памяти не обнаружены в $(basename "$exe")" >> "$report_file"
                        fi
                    else
                        warning "valgrind не установлен, пропускаем проверку утечек памяти в $assignment"
                        echo "ПРЕДУПРЕЖДЕНИЕ: valgrind не установлен, проверка утечек памяти пропущена" >> "$report_file"
                    fi
                fi
            done
        fi
        
        cd "$original_dir"
        echo "" >> "$report_file"
    done
    
    echo "=== ИТОГОВЫЙ БАЛЛ: $total_score/100 ===" >> "$report_file"
    
    if [ $total_score -ge 80 ]; then
        success "Студент $student_name: $total_score/100 баллов (Отлично)"
    elif [ $total_score -ge 60 ]; then
        warning "Студент $student_name: $total_score/100 баллов (Хорошо)"
    elif [ $total_score -ge 40 ]; then
        warning "Студент $student_name: $total_score/100 баллов (Удовлетворительно)"
    else
        error "Студент $student_name: $total_score/100 баллов (Неудовлетворительно)"
    fi
    
    echo "$student_name: $total_score/100"
}

main() {
    log "Начало проверки домашних заданий"
    
    cd "$(dirname "$0")"
    
    local report_dir="/app/reports"
    mkdir -p "$report_dir"
    if [ ! -d "$report_dir" ]; then
        error "Не удалось создать директорию отчетов: $report_dir"
        return 1
    fi
    
    echo "=== СВОДНЫЙ ОТЧЕТ ПО ВСЕМ СТУДЕНТАМ ===" > "$report_dir/summary_report.txt"
    echo "Дата проверки: $(date)" >> "$report_dir/summary_report.txt"
    echo "Рабочая директория: $(pwd)" >> "$report_dir/summary_report.txt"
    echo "" >> "$report_dir/summary_report.txt"
    
    total_students=0
    passed_students=0
    
    log "Поиск папок студентов..."
    for student_dir in /app/student*; do
        if [ -d "$student_dir" ]; then
            student_name=$(basename "$student_dir")
            log "Найден студент: $student_name"
            total_students=$((total_students + 1))
            
            # Запускаем проверку студента и получаем только последнюю строку с оценкой
            result=$(check_student "$student_dir" 2>/dev/null | tail -1)
            
            # Извлекаем число перед слэшем (например, из "student1: 89/100" получаем 89)
            score=$(echo "$result" | grep -o '[0-9]*/' | grep -o '[0-9]*')
            
            if [ -z "$score" ]; then
                score=0
            fi
            
            echo "$student_name: $score баллов" >> "$report_dir/summary_report.txt"
            
            if [ "$score" -ge 40 ]; then
                passed_students=$((passed_students + 1))
            fi
        fi
    done
    
    echo "" >> "$report_dir/summary_report.txt"
    echo "Общая статистика:" >> "$report_dir/summary_report.txt"
    echo "Всего студентов: $total_students" >> "$report_dir/summary_report.txt"
    echo "Прошли (>=40 баллов): $passed_students" >> "$report_dir/summary_report.txt"
    echo "Процент успешности: $(( passed_students * 100 / total_students ))%" >> "$report_dir/summary_report.txt"
    
    log "Проверка завершена. Отчеты сохранены в $report_dir"
}

main "$@"
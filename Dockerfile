FROM ubuntu:22.04

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    clang-format \
    clang-tidy \
    cppcheck \
    valgrind \
    astyle \
    libgtest-dev \
    cmake \
    astyle \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Собираем Google Test
RUN cd /usr/src/gtest && \
    cmake CMakeLists.txt && \
    make && \
    cp lib/*.a /usr/lib/

# Создаем рабочую директорию
WORKDIR /app

# Копируем скрипт проверки
COPY check_homework.sh /app/
RUN chmod +x /app/check_homework.sh

# Создаем директорию для отчетов и даем права
RUN mkdir -p /app/reports && chmod 777 /app/reports

# Устанавливаем пользователя для запуска
USER root

# Копируем конфигурационные файлы
COPY .clang-format /app/
COPY .clang-tidy /app/

CMD ["/bin/bash"]
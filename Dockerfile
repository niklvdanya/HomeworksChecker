FROM ubuntu:22.04

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
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN cd /usr/src/gtest && \
    cmake CMakeLists.txt && \
    make && \
    cp lib/*.a /usr/lib/

WORKDIR /app

COPY check_homework.py /app/
RUN chmod +x /app/check_homework.py

RUN mkdir -p /app/reports

COPY .clang-tidy /app/

CMD ["/bin/bash"]
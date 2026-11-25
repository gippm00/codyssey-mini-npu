from pathlib import Path
import json
from time import perf_counter

pattern = [
    [1, 0, 1],
    [0, 1, 0],
    [1, 0, 1],
]

cross = [
    [0, 1, 0],
    [1, 1, 1],
    [0, 1, 0],
]

x_filter = [
    [1, 0, 1],
    [0, 1, 0],
    [1, 0, 1],
]
def load_data():
    data_path = Path(__file__).resolve().parent / "data.json"
    with data_path.open("r", encoding="utf-8") as file:
        return json.load(file)
    
def normalize_label(label):
    if label == "+" or label.lower() == "cross":
        return "Cross"
    if label.lower() == "x":
        return "X"
    return None

def mac_score(pattern, filter_data):
    score = 0

    for row in range(len(pattern)):
        for col in range(len(pattern[row])):
            score += pattern[row][col] * filter_data[row][col]

    return score

def average_mac_ms(pattern, filter_data, repeats=10):
    start = perf_counter()
    for _ in range(repeats):
        mac_score(pattern, filter_data)
    elapsed = perf_counter() - start
    return elapsed * 1000 / repeats

def classify(cross_score, x_score):
    if abs(cross_score - x_score) < 1e-9:
        return "UNDECIDED"
    if cross_score > x_score:
        return "Cross"
    return "X"

def is_square(matrix, size):
    if not isinstance(matrix, list) or len(matrix) != size:
        return False

    for row in matrix:
        if not isinstance(row, list) or len(row) != size:
            return False

    return True

def read_matrix(name):
    print(f"\n{name} 입력 (한 줄에 숫자 3개를 공백으로 구분)")
    matrix = []

    while len(matrix) < 3:
        values = input(f"{len(matrix) + 1}번째 행: ").split()

        if len(values) != 3:
            print("숫자를 정확히 3개 입력해 주세요.")
            continue

        try:
            row = [float(value) for value in values]
        except ValueError:
            print("숫자만 입력해 주세요.")
            continue

        matrix.append(row)

    return matrix

def run_manual():
    filter_a = read_matrix("필터 A")
    filter_b = read_matrix("필터 B")
    print("필터 A와 B 입력 완료")

    pattern = read_matrix("입력 패턴")
    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)

    result = classify(score_a, score_b)
    labels = {"Cross": "A", "X": "B", "UNDECIDED": "판정 불가"}

    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"판정: {labels[result]}")
    average_ms = average_mac_ms(pattern, filter_a)
    print("\n크기 | 평균 시간(ms) | 연산 횟수")
    print(f"3×3 | {average_ms:.6f} | 9")

def analyze_json(data):
    failed_cases = []
    benchmark_inputs = {3: (cross, cross)}
    for case_name, case_info in data["patterns"].items():
        parts = case_name.split("_")
        if (
            len(parts) != 3
            or parts[0] != "size"
            or parts[1] not in ("5", "13", "25")
            or not parts[2].isdecimal()
        ):
            reason = "케이스 이름이 size_N_idx 형식에 맞지 않음"
            print(f"{case_name}: FAIL | {reason}")
            failed_cases.append((case_name, reason))
            continue

        size_key = "_".join(parts[:2])
        raw_filters = data["filters"][size_key]

        filters = {}
        for raw_label, matrix in raw_filters.items():
            filters[normalize_label(raw_label)] = matrix

        pattern = case_info["input"]
        size = int(size_key.split("_")[1])
        for name, matrix in (
            ("입력 패턴", pattern),
            ("Cross 필터", filters["Cross"]),
            ("X 필터", filters["X"]),
        ):
            if not is_square(matrix, size):
                reason = f"{name}의 크기가 {size}×{size}가 아님"
                print(f"{case_name}: FAIL | {reason}")
                failed_cases.append((case_name, reason))
                break
        else:
            reason = None

        if reason is not None:
            continue
        if size not in benchmark_inputs:
            benchmark_inputs[size] = (pattern, filters["Cross"])
        cross_score = mac_score(pattern, filters["Cross"])
        x_score = mac_score(pattern, filters["X"])

        predicted = classify(cross_score, x_score)
        expected = normalize_label(case_info["expected"])
        status = "PASS" if predicted == expected else "FAIL"

        print(f"{case_name}: Cross 점수={cross_score}, X 점수={x_score}, 판정={predicted}, expected={expected} | {status}")
        if status == "FAIL":
            reason = (
                "두 점수의 차이가 허용오차보다 작아 판정 불가"
                if predicted == "UNDECIDED"
                else f"판정 {predicted}이 정답 {expected}과 다름"
            )
            failed_cases.append((case_name, reason))
    print("\n크기 | 평균 시간(ms) | 연산 횟수")
    for size in sorted(benchmark_inputs):
        sample_pattern, sample_filter = benchmark_inputs[size]
        average_ms = average_mac_ms(sample_pattern, sample_filter)
        print(f"{size}×{size} | {average_ms:.6f} | {size * size}")
    total = len(data["patterns"])
    failed = len(failed_cases)
    print(f"\n전체: {total}건 | 통과: {total - failed}건 | 실패: {failed}건")

    for case_name, reason in failed_cases:
        print(f"- {case_name}: {reason}")

print("1. 3×3 수동 입력")
print("2. data.json 분석")
choice = input("모드 선택: ").strip()

if choice == "1":
    run_manual()
elif choice == "2":
    analyze_json(load_data())
else:
    print("1 또는 2를 선택해 주세요.")
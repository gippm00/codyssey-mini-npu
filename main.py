import argparse
import json
from math import isfinite
from pathlib import Path
from time import perf_counter

EPSILON = 1e-9  # 소수 누산에서 생기는 작은 차이를 동점으로 처리한다.
BENCHMARK_REPEATS = 10
EXPECTED_FILE_SIZES = (5, 13, 25)
LABEL_ALIASES = {"+": "Cross", "cross": "Cross", "x": "X"}

EXAMPLE_CROSS = [
    [0, 1, 0],
    [1, 1, 1],
    [0, 1, 0],
]


def load_data():
    data_path = Path(__file__).resolve().parent / "data.json"
    with data_path.open("r", encoding="utf-8") as file:
        return json.load(file)
    
def normalize_label(label):
    if not isinstance(label, str):
        return None
    return LABEL_ALIASES.get(label.strip().lower())


def mac_score(pattern, filter_data):
    # 같은 위치의 입력과 필터 값을 곱해 누적한 뒤 점수를 반환한다.
    score = 0

    for row in range(len(pattern)):
        for col in range(len(pattern[row])):
            score += pattern[row][col] * filter_data[row][col]

    return score

def average_mac_ms(pattern, filter_data, repeats=BENCHMARK_REPEATS):
    # 측정 구간에는 MAC 함수 호출과 반복문만 포함한다.
    start = perf_counter()
    for _ in range(repeats):
        mac_score(pattern, filter_data)
    elapsed = perf_counter() - start
    return elapsed * 1000 / repeats

def classify(cross_score, x_score):
    if abs(cross_score - x_score) < EPSILON:
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
            print("숫자를 정확히 3개 입력해 주세요. 예: 1.0 0.0 1.0")
            continue

        try:
            row = [float(value) for value in values]
        except ValueError:
            print("숫자만 입력해 주세요. 예: 1.0 0.0 1.0")
            continue

        if not all(isfinite(value) for value in row):
            print("유한한 숫자를 입력해 주세요. 예: 1.0 0.0 1.0")
            continue

        matrix.append(row)

    return matrix

def run_manual(repeats=BENCHMARK_REPEATS):
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
    print(f"\n필터 | 크기 | {repeats}회 평균 시간(ms) | MAC 연산 횟수(필터 1개)")
    for label, filter_data in (("A", filter_a), ("B", filter_b)):
        average_ms = average_mac_ms(pattern, filter_data, repeats)
        print(f"{label} | 3×3 | {average_ms:.6f} | 9")

def case_size_key(case_name):
    parts = case_name.split("_")
    if (
        len(parts) != 3
        or parts[0] != "size"
        or not parts[1].isascii()
        or not parts[1].isdecimal()
        or parts[1].startswith("0")
        or not parts[2].isascii()
        or not parts[2].isdecimal()
    ):
        raise ValueError("케이스 이름이 size_N_idx 형식에 맞지 않음")
    return "_".join(parts[:2])


def is_finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def validate_case(case_name, case_info, filter_groups):
    size_key = case_size_key(case_name)
    raw_filters = filter_groups.get(size_key)
    if not isinstance(raw_filters, dict):
        raise ValueError(f"{size_key} 필터 묶음이 없거나 형식이 잘못됨")

    filters = {}
    for raw_label, matrix in raw_filters.items():
        label = normalize_label(raw_label)
        if label is None:
            raise ValueError(f"지원하지 않는 필터 라벨 {raw_label!r}")
        if label in filters:
            raise ValueError(f"정규화 후 필터 라벨 {label!r}이 중복됨")
        filters[label] = matrix
    if "Cross" not in filters or "X" not in filters:
        raise ValueError("Cross 또는 X 필터가 누락됨")

    if not isinstance(case_info, dict):
        raise ValueError("케이스에 input과 expected가 필요함")
    expected = normalize_label(case_info.get("expected"))
    if expected is None:
        raise ValueError("expected 라벨이 누락됐거나 지원되지 않음")

    pattern = case_info.get("input")
    size = int(size_key.split("_")[1])
    for name, matrix in (
        ("입력 패턴", pattern),
        ("Cross 필터", filters["Cross"]),
        ("X 필터", filters["X"]),
    ):
        if not is_square(matrix, size):
            raise ValueError(f"{name}의 크기가 {size}×{size}가 아님")
        if not all(is_finite_number(value) for row in matrix for value in row):
            raise ValueError(f"{name}에 유한한 숫자가 아닌 값이 있음")
    return size, pattern, filters, expected


def analyze_json(data, repeats=BENCHMARK_REPEATS):
    if not isinstance(data, dict) or not isinstance(data.get("patterns"), dict):
        print("데이터 오류: patterns 항목은 객체여야 합니다.")
        return
    filter_groups = data.get("filters")
    if not isinstance(filter_groups, dict):
        print("데이터 오류: filters 항목이 없거나 형식이 잘못됐습니다.")
        filter_groups = {}

    patterns = data["patterns"]
    failed_cases = []
    undecided = 0
    benchmark_inputs = {3: (EXAMPLE_CROSS, EXAMPLE_CROSS)}

    for case_name, case_info in patterns.items():
        try:
            size, pattern, filters, expected = validate_case(
                case_name, case_info, filter_groups
            )
            cross_score = mac_score(pattern, filters["Cross"])
            x_score = mac_score(pattern, filters["X"])
            if not is_finite_number(cross_score) or not is_finite_number(x_score):
                raise ValueError("두 필터 점수는 유한한 숫자여야 함")
        except ValueError as error:
            reason = str(error)
            print(f"{case_name}: FAIL | {reason}")
            failed_cases.append((case_name, reason))
            continue

        if size not in benchmark_inputs:
            benchmark_inputs[size] = (pattern, filters["Cross"])
        predicted = classify(cross_score, x_score)
        status = "PASS" if predicted == expected else "FAIL"
        print(
            f"{case_name}: Cross 점수={cross_score}, X 점수={x_score}, "
            f"판정={predicted}, expected={expected} | {status}"
        )
        if predicted == "UNDECIDED":
            undecided += 1
            difference = abs(cross_score - x_score)
            reason = (
                f"판정 불가 (Cross={cross_score}, X={x_score}, "
                f"절대 차이={difference:.3g}, 허용오차={EPSILON:g})"
            )
        elif status == "FAIL":
            reason = f"판정 {predicted}이 정답 {expected}과 다름"
        if status == "FAIL":
            failed_cases.append((case_name, reason))

    print(
        f"\n크기 | {repeats}회 평균 시간(ms) | "
        "MAC(필터 1개) | MAC(필터 2개 판정)"
    )
    for size in sorted(benchmark_inputs.keys() | set(EXPECTED_FILE_SIZES)):
        operations = size * size
        if size in benchmark_inputs:
            sample_pattern, sample_filter = benchmark_inputs[size]
            average = f"{average_mac_ms(sample_pattern, sample_filter, repeats):.6f}"
        else:
            average = "측정 불가"
        print(f"{size}×{size} | {average} | {operations} | {2 * operations}")

    total = len(patterns)
    failed = len(failed_cases)
    passed = total - failed
    pass_rate = f"{100 * passed / total:.1f}%" if total else "해당 없음"
    print(
        f"\n전체: {total}건 | 통과: {passed}건 | 실패: {failed}건 | 통과율: {pass_rate}"
    )
    print(f"판정 불가(실패에 포함): {undecided}건")
    for case_name, reason in failed_cases:
        print(f"- {case_name}: {reason}")


def main():
    parser = argparse.ArgumentParser(description="Mini NPU 시뮬레이터")
    parser.add_argument("--repeats", type=int, default=BENCHMARK_REPEATS,
                        help="표의 연산 시간 측정 반복 횟수 (기본 10회)")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats는 1 이상의 정수여야 합니다.")

    print("1. 3×3 수동 입력")
    print("2. data.json 분석")
    choice = input("모드 선택: ").strip()

    if choice == "1":
        run_manual(args.repeats)
    elif choice == "2":
        try:
            data = load_data()
        except (OSError, ValueError) as error:
            print(f"data.json 읽기 실패: {error}")
            return
        analyze_json(data, args.repeats)
    else:
        print("1 또는 2를 선택해 주세요.")


if __name__ == "__main__":
    main()

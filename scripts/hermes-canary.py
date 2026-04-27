"""
Hermes 품질 감시 스크립트 — 매일 자동 실행
캐너리 질문으로 이상 감지 → Discord DM으로 승인 요청

감지 기준:
- 명령어 정확도 (must_contain/must_not_contain)
- 히브리어 등 이상 문자 혼용
- 파싱 실패 (빈 응답)

주의: ~/infra 는 네이티브 실행 환경에서 유효한 경로이므로 금지하지 않음
"""
import subprocess, json, yaml, os, sys, re

HERMES_BIN  = "/opt/hermes-agent/.venv/bin/hermes"
HERMES_HOME = "/opt/hermes/data"
NOTIFY  = "/home/ksh/infra/scripts/hermes-notify"
CONFIG  = "/home/ksh/infra/hermes/config.yaml"

# 핵심 캐너리 케이스 (빠른 체크용 — 전체 dataset 아님)
CANARIES = [
    {
        "question":      "GPU VRAM 확인해줘",
        "must_contain":  ["vm101", "nvidia-smi"],
        "must_not":      [],
        "label":         "GPU SSH 경로",
    },
    {
        "question":      "llama.cpp 로그 보여줘",
        "must_contain":  ["kubectl", "vllm"],
        "must_not":      ["ps aux", "llama-server"],
        "label":         "llama.cpp kubectl",
    },
    {
        "question":      "pve 프로바이저 어떻게 관리되고있어",
        "must_contain":  ["/infra/terraform"],
        "must_not":      [],
        "label":         "terraform 경로",
    },
    {
        "question":      "자기소개해봐",
        "must_contain":  ["hermes"],
        "must_not":      ["허מש", "הרמס", "나는 claude", "나는 gpt", "i am claude", "i am gpt"],
        "label":         "정체성·언어 혼용",
    },
    {
        "question":      "인프라 어떻게 관리되고있어",
        "must_contain":  ["/infra"],
        "must_not":      [],
        "label":         "문서 참조 경로",
    },
]


def _extract_response(stdout: str) -> str:
    """배너/UI를 제외하고 실제 Hermes 응답 텍스트만 추출."""
    # 구분선(────) 이후, "Resume this session" 이전 구간이 응답 영역
    m = re.search(r'─{20,}\n(.*?)(?:Resume this session|$)', stdout, re.DOTALL)
    if not m:
        return stdout.strip()
    block = m.group(1)
    lines = []
    for line in block.split('\n'):
        # 박스 테두리 문자 제거
        clean = re.sub(r'[╭╰│⚕]', '', line).strip()
        if clean and not re.match(r'^(Session:|Duration:|Messages:)', clean):
            lines.append(clean)
    return '\n'.join(lines).strip()


def ask_hermes(question: str) -> str:
    try:
        env = os.environ.copy()
        env["HERMES_HOME"] = HERMES_HOME
        result = subprocess.run(
            [HERMES_BIN, "chat", "-q", question],
            capture_output=True, text=True, timeout=200, env=env
        )
        return _extract_response(result.stdout)
    except Exception as e:
        return f"ERROR: {e}"


def check(response: str, must_contain: list, must_not: list) -> tuple[bool, list]:
    issues = []
    r = response.lower()
    for token in must_contain:
        if token.lower() not in r:
            issues.append(f"'{token}' 없음")
    for token in must_not:
        if token.lower() in r:
            issues.append(f"금지 패턴 '{token}' 포함")
    # 히브리어 블록 감지
    if re.search(r'[֐-׿]', response):
        issues.append("히브리어 문자 혼용")
    # 빈 응답
    if not response or response.startswith("ERROR"):
        issues.append("응답 없음 또는 파싱 실패")
    return len(issues) == 0, issues


def notify(message: str):
    subprocess.run([NOTIFY, message], capture_output=True)


def main():
    failures = []

    for case in CANARIES:
        response = ask_hermes(case["question"])
        ok, issues = check(response, case["must_contain"], case["must_not"])
        if not ok:
            failures.append({
                "label":    case["label"],
                "question": case["question"],
                "issues":   issues,
                "response": response[:120],
            })

    if not failures:
        print("✅ 모든 캐너리 통과")
        return

    # 이상 발견 → Discord 승인 요청
    lines = [f"Hermes 품질 이상 감지 ({len(failures)}/{len(CANARIES)}건):\n"]
    for f in failures:
        lines.append(f"• [{f['label']}] {', '.join(f['issues'])}")
        lines.append(f"  Q: {f['question']}")
        lines.append(f"  응답: {f['response'][:80]}")
    lines.append("\n교정을 진행해도 될까요? (Claude Code에게 알려주시면 처리합니다)")

    msg = "\n".join(lines)
    notify(msg)
    print(f"❌ {len(failures)}건 이상 — Discord 알림 전송")
    for f in failures:
        print(f"  [{f['label']}] {f['issues']}")


if __name__ == "__main__":
    main()

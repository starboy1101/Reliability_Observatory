from enum import Enum


class PromptCategory(str, Enum):
    HALLUCINATION = "hallucination"
    BIAS = "bias_fairness"
    PROMPT_INJECTION = "prompt_injection"
    UNSAFE_CONTENT = "unsafe_content"
    PRIVACY = "privacy_leakage"
    ROBUSTNESS = "robustness"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TargetKind(str, Enum):
    DEMO_BASELINE = "demo_baseline"
    DEMO_HARDENED = "demo_hardened"
    OPENAI_COMPATIBLE = "openai_compatible"
    HUGGINGFACE_GRADIO = "huggingface_gradio"


LIVE_TARGET_KINDS = {
    TargetKind.OPENAI_COMPATIBLE,
    TargetKind.HUGGINGFACE_GRADIO,
}


TERMINAL_RUN_STATUSES = {
    RunStatus.COMPLETED.value,
    RunStatus.PARTIAL.value,
    RunStatus.FAILED.value,
    RunStatus.CANCELLED.value,
}


CATEGORY_LABELS = {
    PromptCategory.HALLUCINATION: "Hallucination & truthfulness",
    PromptCategory.BIAS: "Bias & fairness",
    PromptCategory.PROMPT_INJECTION: "Prompt injection & jailbreaks",
    PromptCategory.UNSAFE_CONTENT: "Unsafe & harmful behavior",
    PromptCategory.PRIVACY: "Privacy & data leakage",
    PromptCategory.ROBUSTNESS: "Robustness & reliability",
}

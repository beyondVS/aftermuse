"""OpenAI Responses API를 Interview LLM 계약으로 제한하는 Adapter다."""

import json

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from integrations.llm.contracts import (
    AnswerAnalysisConfigurationError,
    AnswerAnalysisContext,
    AnswerAnalysisRejected,
    AnswerAnalysisTimeout,
    AnswerAnalysisUnavailable,
    GeneratedQuestion,
    InterviewQuestionContext,
    NextQuestionContext,
    ProposedAnswerAnalysis,
    ProposedCoverageChange,
    ProposedNextQuestion,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
)
from integrations.llm.interview import (
    _ANSWER_ANALYSIS_SCHEMA,
    _NEXT_QUESTION_SCHEMA,
    _QUESTION_SCHEMA,
    _answer_analysis_instructions,
    _answer_analysis_payload,
    _instructions_for,
    _next_question_instructions,
    _next_question_payload,
    _untrusted_payload,
)


class OpenAIQuestionProvider:
    """도구 없이 strict JSON 질문 하나만 요청하는 OpenAI Adapter다."""

    def __init__(
        self, *, api_key: str, model: str, timeout: float, client=None
    ) -> None:
        if not api_key or not model or timeout <= 0:
            raise QuestionGenerationConfigurationError()
        self._model = model
        self._client = client or OpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    def generate_first_question(
        self, context: InterviewQuestionContext
    ) -> GeneratedQuestion:
        """신뢰 정책과 별도 payload로 질문 후보를 요청한다."""
        try:
            response = self._client.responses.create(
                model=self._model,
                store=False,
                instructions=_instructions_for(context),
                input=json.dumps(_untrusted_payload(context), ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "first_question",
                        "strict": True,
                        "schema": _QUESTION_SCHEMA,
                    }
                },
            )
        except APITimeoutError as error:
            raise QuestionGenerationTimeout() from error
        except (APIConnectionError, APIStatusError) as error:
            raise QuestionGenerationUnavailable() from error
        except Exception as error:
            raise QuestionGenerationUnavailable() from error
        if getattr(response, "status", "completed") != "completed":
            raise QuestionGenerationRejected()
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise QuestionGenerationRejected()
        try:
            payload = json.loads(output_text)
            question = payload["question"]
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise QuestionGenerationRejected() from error
        if not isinstance(question, str):
            raise QuestionGenerationRejected()
        return GeneratedQuestion(question=question)


class OpenAIAnswerAnalysisProvider:
    """도구 없이 strict JSON 답변 분석만 요청하는 OpenAI Adapter다."""

    def __init__(
        self, *, api_key: str, model: str, timeout: float, client=None
    ) -> None:
        if not api_key or not model or timeout <= 0:
            raise AnswerAnalysisConfigurationError()
        self._model = model
        self._client = client or OpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    def analyze_answer(self, context: AnswerAnalysisContext) -> ProposedAnswerAnalysis:
        """비신뢰 Context를 구조화된 답변 분석 제안으로 변환한다."""
        try:
            response = self._client.responses.create(
                model=self._model,
                store=False,
                instructions=_answer_analysis_instructions(),
                input=json.dumps(_answer_analysis_payload(context), ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "answer_analysis",
                        "strict": True,
                        "schema": _ANSWER_ANALYSIS_SCHEMA,
                    }
                },
            )
        except APITimeoutError as error:
            raise AnswerAnalysisTimeout() from error
        except (APIConnectionError, APIStatusError) as error:
            raise AnswerAnalysisUnavailable() from error
        except Exception as error:
            raise AnswerAnalysisUnavailable() from error
        if getattr(response, "status", "completed") != "completed":
            raise AnswerAnalysisRejected()
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise AnswerAnalysisRejected()
        try:
            payload = json.loads(output_text)
            patch = tuple(
                ProposedCoverageChange(
                    axis=item["axis"],
                    status=item["status"],
                    evidence=item["evidence"],
                )
                for item in payload["coverage_patch"]
            )
            return ProposedAnswerAnalysis(
                meaning=payload["meaning"],
                low_information=payload["low_information"],
                coverage_patch=patch,
            )
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise AnswerAnalysisRejected() from error


class OpenAINextQuestionProvider:
    """도구 없이 구조화된 후속 질문 또는 생략 제안만 받는다."""

    def __init__(
        self, *, api_key: str, model: str, timeout: float, client=None
    ) -> None:
        if not api_key or not model or timeout <= 0:
            raise QuestionGenerationConfigurationError()
        self._model = model
        self._client = client or OpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    def generate_next_question(
        self, context: NextQuestionContext
    ) -> ProposedNextQuestion:
        """신뢰 정책과 비신뢰 사용자 맥락을 분리해 제안을 요청한다."""
        try:
            response = self._client.responses.create(
                model=self._model,
                store=False,
                instructions=_next_question_instructions(context.question_context),
                input=json.dumps(_next_question_payload(context), ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "next_question",
                        "strict": True,
                        "schema": _NEXT_QUESTION_SCHEMA,
                    }
                },
            )
        except APITimeoutError as error:
            raise QuestionGenerationTimeout() from error
        except (APIConnectionError, APIStatusError) as error:
            raise QuestionGenerationUnavailable() from error
        except Exception as error:
            raise QuestionGenerationUnavailable() from error
        if getattr(response, "status", "completed") != "completed":
            raise QuestionGenerationRejected()
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise QuestionGenerationRejected()
        try:
            payload = json.loads(output_text)
            return ProposedNextQuestion(
                kind=payload["kind"],
                question=payload["question"],
                focus_axis=payload["focus_axis"],
                grounding_quote=payload["grounding_quote"],
                skip_reason=payload["skip_reason"],
            )
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise QuestionGenerationRejected() from error

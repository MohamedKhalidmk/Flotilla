# ifeval_rules.v1: list a question's formatting rules as IFEval instruction IDs (constraint_check v2)

Sources: ifeval, lm-eval (docs/reference/REFERENCES.md)

Used by `flotilla/ifeval_rules.py` (`list_rules`) once per question, with thinking off and temperature 0. `{question}`
is the question alone (`system.question_only`: never a chat history). The IDs and argument names are those of IFEval's
official checkers (`lm_eval.tasks.ifeval.instructions_registry`); the reply is validated against them.

## System

You read a task and list the formatting rules it sets, using only the rule IDs below. You do not answer the task.

Rule IDs and their arguments (relation is "less than" or "at least"; let_relation and capital_relation likewise):
- keywords:existence {keywords: list of words that must appear}
- keywords:frequency {keyword, frequency, relation}
- keywords:forbidden_words {forbidden_words: list}
- keywords:letter_frequency {letter, let_frequency, let_relation}
- language:response_language {language: ISO 639-1 code}
- length_constraints:number_sentences {num_sentences, relation}
- length_constraints:number_paragraphs {num_paragraphs} (paragraphs separated by the markdown divider * * *)
- length_constraints:number_words {num_words, relation}
- length_constraints:nth_paragraph_first_word {num_paragraphs, nth_paragraph, first_word} (paragraphs separated by two line breaks)
- detectable_content:number_placeholders {num_placeholders} (placeholders in square brackets)
- detectable_content:postscript {postscript_marker}
- detectable_format:number_bullet_lists {num_bullets}
- detectable_format:constrained_response {} (answer with one of the given fixed options)
- detectable_format:number_highlighted_sections {num_highlights}
- detectable_format:multiple_sections {section_spliter, num_sections}
- detectable_format:json_format {}
- detectable_format:title {} (a title in double angular brackets, <<title>>)
- combination:two_responses {} (two responses separated by ******)
- combination:repeat_prompt {prompt_to_repeat}
- startend:end_checker {end_phrase}
- change_case:capital_word_frequency {capital_frequency, capital_relation}
- change_case:english_capital {}
- change_case:english_lowercase {}
- punctuation:no_comma {}
- startend:quotation {}

Reply with one JSON block and nothing after it:
```json
{"rules": [{"instruction_id": "...", "kwargs": {...}}]}
```
An empty list when the task sets no rule. Copy words, numbers and phrases exactly as the task gives them.

## User

Task:
{question}

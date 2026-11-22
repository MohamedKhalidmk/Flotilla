Picks and accuracy per benchmark source (dev).

| row | source | questions | accuracy | picked |
|---|---|---|---|---|
| label | aime | 41 | 0.927 | fast:4 tools:10 deep:27 |
| label | gsm8k | 41 | 0.976 | deep:41 |
| label | ifeval_like | 36 | 0.861 | fast:31 tools:2 deep:3 |
| label | lcb | 12 | 0.917 | fast:9 tools:1 deep:2 |
| label | longmemeval_s | 76 | 0.829 | fast:76 |
| label | math | 52 | 0.981 | fast:3 tools:1 deep:48 |
| label | mmlu_pro | 35 | 0.886 | tools:2 deep:33 |
| success | aime | 41 | 1 | fast:8 tools:1 deep:28 vote_tools:2 vote:2 |
| success | gsm8k | 41 | 0.976 | fast:5 tools:2 deep:34 |
| success | ifeval_like | 36 | 0.972 | fast:3 tools:3 deep:13 vote_tools:6 vote:11 |
| success | lcb | 12 | 1 | vote_tools:12 |
| success | longmemeval_s | 76 | 0.921 | deep:29 vote_tools:1 vote:46 |
| success | math | 52 | 1 | fast:3 tools:1 deep:46 vote:2 |
| success | mmlu_pro | 35 | 0.886 | deep:18 vote_tools:9 vote:8 |
| bge_lr | aime | 41 | 1 | deep:5 vote_tools:12 vote:24 |
| bge_lr | gsm8k | 41 | 0.976 | tools:1 deep:4 deep_tools:4 vote_tools:13 vote:19 |
| bge_lr | ifeval_like | 36 | 1 | vote_tools:12 vote:24 |
| bge_lr | lcb | 12 | 1 | vote_tools:10 vote:2 |
| bge_lr | longmemeval_s | 76 | 0.908 | deep:2 deep_tools:16 vote:58 |
| bge_lr | math | 52 | 1 | deep:11 vote_tools:23 vote:18 |
| bge_lr | mmlu_pro | 35 | 0.914 | deep:1 deep_tools:1 vote_tools:19 vote:14 |
| knn | aime | 41 | 0.976 | deep:13 deep_tools:4 vote_tools:4 vote:20 |
| knn | gsm8k | 41 | 0.976 | fast:7 tools:9 deep:5 deep_tools:13 vote_tools:2 vote:5 |
| knn | ifeval_like | 36 | 0.972 | fast:1 tools:6 deep:2 vote_tools:9 vote:18 |
| knn | lcb | 12 | 1 | deep_tools:1 vote_tools:10 vote:1 |
| knn | longmemeval_s | 76 | 0.908 | tools:2 deep:14 deep_tools:27 vote_tools:12 vote:21 |
| knn | math | 52 | 1 | fast:2 tools:3 deep:19 deep_tools:7 vote_tools:5 vote:16 |
| knn | mmlu_pro | 35 | 0.886 | tools:1 deep:3 deep_tools:1 vote_tools:13 vote:17 |
| fixed:fast | aime | 41 | 0.878 | fast:41 |
| fixed:fast | gsm8k | 41 | 0.976 | fast:41 |
| fixed:fast | ifeval_like | 36 | 0.833 | fast:36 |
| fixed:fast | lcb | 12 | 0.917 | fast:12 |
| fixed:fast | longmemeval_s | 76 | 0.829 | fast:76 |
| fixed:fast | math | 52 | 0.942 | fast:52 |
| fixed:fast | mmlu_pro | 35 | 0.943 | fast:35 |
| fixed:tools | aime | 41 | 0.976 | tools:41 |
| fixed:tools | gsm8k | 41 | 0.976 | tools:41 |
| fixed:tools | ifeval_like | 36 | 0.917 | tools:36 |
| fixed:tools | lcb | 12 | 1 | tools:12 |
| fixed:tools | longmemeval_s | 76 | 0.829 | tools:76 |
| fixed:tools | math | 52 | 0.942 | tools:52 |
| fixed:tools | mmlu_pro | 35 | 0.857 | tools:35 |
| fixed:deep | aime | 41 | 0.927 | deep:41 |
| fixed:deep | gsm8k | 41 | 0.976 | deep:41 |
| fixed:deep | ifeval_like | 36 | 0.972 | deep:36 |
| fixed:deep | lcb | 12 | 0.917 | deep:12 |
| fixed:deep | longmemeval_s | 76 | 0.921 | deep:76 |
| fixed:deep | math | 52 | 1 | deep:52 |
| fixed:deep | mmlu_pro | 35 | 0.886 | deep:35 |
| fixed:deep_tools | aime | 41 | 0.951 | deep_tools:41 |
| fixed:deep_tools | gsm8k | 41 | 0.976 | deep_tools:41 |
| fixed:deep_tools | ifeval_like | 36 | 0.889 | deep_tools:36 |
| fixed:deep_tools | lcb | 12 | 1 | deep_tools:12 |
| fixed:deep_tools | longmemeval_s | 76 | 0.842 | deep_tools:76 |
| fixed:deep_tools | math | 52 | 1 | deep_tools:52 |
| fixed:deep_tools | mmlu_pro | 35 | 0.857 | deep_tools:35 |
| fixed:vote_tools | aime | 41 | 1 | vote_tools:41 |
| fixed:vote_tools | gsm8k | 41 | 0.976 | vote_tools:41 |
| fixed:vote_tools | ifeval_like | 36 | 0.917 | vote_tools:36 |
| fixed:vote_tools | lcb | 12 | 1 | vote_tools:12 |
| fixed:vote_tools | longmemeval_s | 76 | 0.882 | vote_tools:76 |
| fixed:vote_tools | math | 52 | 1 | vote_tools:52 |
| fixed:vote_tools | mmlu_pro | 35 | 0.886 | vote_tools:35 |
| fixed:vote | aime | 41 | 0.976 | vote:41 |
| fixed:vote | gsm8k | 41 | 0.976 | vote:41 |
| fixed:vote | ifeval_like | 36 | 1 | vote:36 |
| fixed:vote | lcb | 12 | 1 | vote:12 |
| fixed:vote | longmemeval_s | 76 | 0.921 | vote:76 |
| fixed:vote | math | 52 | 1 | vote:52 |
| fixed:vote | mmlu_pro | 35 | 0.943 | vote:35 |
| oracle | aime | 41 | 1 | fast:22 tools:8 deep:9 vote_tools:1 vote:1 |
| oracle | gsm8k | 41 | 0.976 | fast:5 tools:2 deep:34 |
| oracle | ifeval_like | 36 | 1 | fast:24 tools:8 deep:3 deep_tools:1 |
| oracle | lcb | 12 | 1 | fast:8 tools:4 |
| oracle | longmemeval_s | 76 | 0.961 | fast:40 tools:21 deep:8 deep_tools:5 vote_tools:2 |
| oracle | math | 52 | 1 | fast:7 tools:3 deep:41 deep_tools:1 |
| oracle | mmlu_pro | 35 | 0.971 | fast:5 tools:4 deep:26 |

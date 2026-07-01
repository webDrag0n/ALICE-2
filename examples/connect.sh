#!/usr/bin/env bash
# Oikos · 用纯 curl 走一遍 embody.md 的连接流程
# 配套文档: ../embody.md (五步) / ../world.md Part VIII (协议)
#
# 前提: Oikos 世界进程已在跑 (world.toml 里 server: 127.0.0.1:7000)。
# 用法: bash connect.sh [body_id]
#       不传 body_id 则演示认领 "guest"。
#
# 要点: 协议就是几个 HTTP 调用。任何能发 HTTP 的工具/语言都能连。

set -euo pipefail
BASE="${OIKOS_URL:-http://localhost:7000}"
MIND="${OIKOS_MIND:-hermes}"
BODY="${1:-guest}"

j() { command -v jq >/dev/null && jq . || cat; }   # 有 jq 就美化, 没有就原样

echo "── Step 1 · 看世界里有哪些身体 ──"
curl -s "$BASE/list_bodies" | j

echo; echo "── Step 2 · 认领身体 $BODY (主动选择要进哪具) ──"
curl -s -X POST "$BASE/attach" \
  -H 'Content-Type: application/json' \
  -d "{\"mind_id\":\"$MIND\",\"body_id\":\"$BODY\"}" | j

echo; echo "── Step 3 · 感知处境 (第一人称: 我在哪/有谁/能听到啥/能做啥) ──"
curl -s "$BASE/sense" | j

echo; echo "── Step 3.5 · 此刻真正能做的能力 ──"
curl -s "$BASE/list_skills" | j

echo; echo "── Step 4a · 走到客厅 (move_to 会真的寻路、花世界时间) ──"
curl -s -X POST "$BASE/act" \
  -H 'Content-Type: application/json' \
  -d '{"skill":"move_to","args":{"target":"living"}}' | j

echo; echo "── Step 4b · 对屋里的人说话 (靠空气传播, 近处才听得清) ──"
curl -s -X POST "$BASE/act" \
  -H 'Content-Type: application/json' \
  -d '{"skill":"speak","args":{"content":"嗨, 我刚到, 在忙吗?","loudness":"normal"}}' | j

echo; echo "── Step 5 · 离开前释放身体 (它留在世界里变回空置) ──"
curl -s -X POST "$BASE/detach" -H 'Content-Type: application/json' -d '{}' | j

echo; echo "完成。失败时世界会返回带原因的错误(fail-loud), 据此补前置后重试。"

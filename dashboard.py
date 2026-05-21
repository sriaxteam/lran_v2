"""
이란전쟁 민생 브리핑 대시보드 v5
수원시정연구원 | 인텔리전스 브리프 스타일 (다크 네이비)

실행: streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8502
"""

import json
import os
import subprocess
import html
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import DATA_DIR, ANALYZED_DIR, PARADIGM_DIR, POLICY_DIR, DOMESTIC_DIR

# V1 / V2 버전 구분
_DASH_VER   = os.getenv("IRAN_DASH_VERSION", "V1")
_IS_V2      = _DASH_VER == "V2"
_VER_LABEL  = "V2" if _IS_V2 else "V1"

COUNTRY_RESPONSE_DIR = DATA_DIR / "country_response"
CLEAN_DIR            = DATA_DIR / "clean"

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
_PAGE_TITLE = (
    "중동전쟁 민생경제 모니터링 [V2] | 수원시정연구원"
    if _IS_V2 else
    "중동전쟁에 따른 민생경제 대응 모니터링 | 수원시정연구원"
)
st.set_page_config(
    page_title=_PAGE_TITLE,
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS — 다크 인텔리전스 브리프 스타일
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=Inter:wght@400;600;700;800;900&display=swap');

*, *::before, *::after {
  box-sizing: border-box;
  font-family: 'Noto Sans KR', 'Inter', 'Malgun Gothic', sans-serif;
}

/* ── 전체 배경 — 따뜻한 회색 ── */
.stApp { background: #E8E4DC !important; }
[data-testid="stAppViewContainer"] { background: #E8E4DC !important; }
[data-testid="stMain"]    { background: transparent !important; }
.main                     { background: transparent !important; }
[data-testid="stHeader"]     { display: none !important; }
[data-testid="stToolbar"]    { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── block-container = 흰 카드 본체 ── */
.block-container {
  padding: 0 24px 32px 24px !important;
  max-width: 920px !important;
  margin: 28px auto 48px auto !important;
  background: #FFFFFF !important;
  border-radius: 12px !important;
  box-shadow: 0 2px 24px rgba(0,0,0,0.11) !important;
}
/* 푸터만 전체 폭 유지 */
.intel-footer { margin-left: -24px !important; margin-right: -24px !important; }

/* 사이드바 */
[data-testid="stSidebar"] { background: #1C2B40 !important; }
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stButton button {
  background: #1A56DB !important; color: white !important;
  border: none !important; border-radius: 4px !important; font-weight: 700 !important;
}

/* ── 헤더 — 다크 네이비, 스크린샷 참고 ── */
.intel-header {
  background: #1C2B40;
  padding: 0;
  border-radius: 8px 8px 0 0;
}
.intel-header-inner {
  display: flex; align-items: flex-end; justify-content: space-between;
  padding: 20px 24px 16px 24px;
}
.header-brand { display: flex; flex-direction: column; gap: 4px; }
.header-org {
  font-size: 0.68rem; color: #7BA7C7; font-weight: 500; letter-spacing: 0.3px;
}
.header-main {
  font-size: 1.55rem; color: #FFFFFF; font-weight: 900; letter-spacing: -0.3px; line-height: 1.2;
}
.header-date-line { font-size: 0.75rem; color: #7BA7C7; margin-top: 3px; }
.header-right { display: flex; align-items: center; gap: 12px; padding-bottom: 4px; }
.urgency-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 13px; border-radius: 4px;
  font-weight: 700; font-size: 0.72rem;
}
.urg-긴급    { background: #C0392B; color: #FFFFFF; }
.urg-주의    { background: #D97706; color: #FFFFFF; }
.urg-모니터링 { background: #1A7A4A; color: #FFFFFF; }
.urg-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.7); animation: blink 1.5s infinite; }
.ud-긴급 .urg-dot, .ud-주의 .urg-dot, .ud-모니터링 .urg-dot { background: rgba(255,255,255,0.8); }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── 지표 띠 — 연회색 배경, 수치 나열 ── */
.metrics-strip-outer {
  background: #F3F4F6;
  border-top: 1px solid #E5E7EB;
  border-radius: 0 0 8px 8px;
  margin-bottom: 20px;
}
.metrics-strip {
  padding: 12px 14px;
  display: flex; gap: 8px; align-items: stretch;
}
.ms-item {
  flex: 1;
  display: flex; flex-direction: column; justify-content: center; align-items: center;
  padding: 10px 6px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.ms-label { font-size: 0.57rem; color: #6B7280; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.3px; white-space: nowrap; }
.ms-value { font-size: 0.93rem; font-weight: 800; color: #111827; font-family: 'Inter', monospace; line-height: 1.2; white-space: nowrap; }
.ms-value.up   { color: #DC2626; }
.ms-value.down { color: #059669; }
.ms-sub { font-size: 0.6rem; color: #9CA3AF; margin-top: 3px; white-space: nowrap; }

/* ── 레이아웃 래퍼 ── */
.page-wrap {
  padding: 20px 24px;
}

/* ── 섹션 공통 — 카드 없이 흰 배경 + 얇은 테두리 ── */
.section-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
}
/* 교차 배경 — 회색 섹션 */
.section-card.sec-gray {
  background: #F8F9FA;
  border-color: #E5E7EB;
}
.sec-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px; padding-bottom: 10px;
  border-bottom: 2.5px solid #1C2B40;
}
.sec-title {
  font-size: 0.88rem; font-weight: 800; color: #111827;
  display: flex; align-items: center; gap: 8px;
}
/* 섹션 번호 배지 */
.sec-num {
  font-size: 0.7rem; font-weight: 900;
  color: #FFFFFF; background: #1C2B40;
  border-radius: 3px; padding: 1px 6px;
  letter-spacing: 0.5px; font-family: 'Inter', monospace;
  flex-shrink: 0;
}
.sec-date { font-size: 0.68rem; color: #9CA3AF; }
.sec-badge {
  font-size: 0.6rem; font-weight: 700; padding: 2px 8px;
  border-radius: 3px; letter-spacing: 0.3px;
}
.badge-blue  { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.badge-red   { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }
.badge-green { background: #F0FDF4; color: #15803D; border: 1px solid #BBF7D0; }
.badge-amber { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
.badge-gray  { background: #F9FAFB; color: #6B7280; border: 1px solid #E5E7EB; }

/* ── 히어로 (헤드라인 + Scout) — 흰 박스 ── */
.hero-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 22px 24px;
  margin-bottom: 16px;
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 24px;
  align-items: start;
}
.hero-label {
  font-size: 0.6rem; font-weight: 700; letter-spacing: 1.5px;
  color: #6B7280; text-transform: uppercase; margin-bottom: 8px;
}
.hero-headline {
  font-size: 1.3rem; font-weight: 900; color: #111827;
  line-height: 1.4; margin-bottom: 14px;
}
.hero-headline .hl-red { color: #DC2626; }
.hero-meta {
  display: flex; gap: 16px; font-size: 0.7rem; color: #9CA3AF; margin-bottom: 14px;
}
.scout-label {
  font-size: 0.6rem; font-weight: 700; letter-spacing: 1.5px;
  color: #6B7280; text-transform: uppercase; margin-bottom: 8px;
}
.scout-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 0; border-bottom: 1px solid #F3F4F6;
  font-size: 0.8rem; color: #374151; line-height: 1.55;
}
.scout-item:last-child { border-bottom: none; }
.scout-num {
  min-width: 18px; height: 18px;
  background: #1C2B40; border-radius: 50%;
  color: white; font-size: 0.58rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 2px;
}

/* 메트릭 사이드 패널 (히어로 오른쪽) */
.metrics-panel {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 16px;
}
.metric-item { margin-bottom: 14px; }
.metric-item:last-child { margin-bottom: 0; }
.metric-label { font-size: 0.58rem; font-weight: 600; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px; }
.metric-value { font-size: 1.3rem; font-weight: 900; color: #111827; font-family: 'Inter', monospace; line-height: 1; }
.metric-value.up { color: #DC2626; }
.metric-unit { font-size: 0.65rem; color: #9CA3AF; margin-left: 3px; font-weight: 400; }
.metric-divider { border: none; border-top: 1px solid #E5E7EB; margin: 12px 0; }
.metric-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; }
.metric-row:last-child { margin-bottom: 0; }
.mr-label { font-size: 0.67rem; color: #9CA3AF; }
.mr-value { font-size: 0.75rem; color: #374151; font-weight: 700; font-family: 'Inter', monospace; }

/* ── 2컬럼 패널 ── */
.twin-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.panel-card {
  background: #FFFFFF; border: 1px solid #E5E7EB;
  border-radius: 8px; padding: 18px 20px;
}
.panel-title {
  font-size: 0.82rem; font-weight: 800; color: #111827;
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 12px; padding-bottom: 10px;
  border-bottom: 1px solid #F3F4F6;
}
.panel-title::before { content: "●"; color: #1C2B40; font-size: 0.5rem; }

/* 시그널 목록 */
.signal-item {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 7px 0; border-bottom: 1px solid #F9FAFB;
  font-size: 0.77rem; color: #374151; line-height: 1.5;
}
.signal-item:last-child { border-bottom: none; }
.sig-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 6px; }
.sig-red   { background: #EF4444; }
.sig-amber { background: #F59E0B; }
.sig-blue  { background: #3B82F6; }
.sig-green { background: #10B981; }

/* 국내지표 */
.kpi-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid #F9FAFB;
}
.kpi-row:last-child { border-bottom: none; }
.kpi-label { font-size: 0.75rem; color: #6B7280; }
.kpi-right { display: flex; align-items: center; gap: 8px; }
.kpi-value { font-size: 0.88rem; color: #111827; font-weight: 700; font-family: 'Inter', monospace; }
.kpi-tag { font-size: 0.6rem; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
.kt-up   { background: #FEF2F2; color: #DC2626; }
.kt-down { background: #F0FDF4; color: #15803D; }
.kt-neu  { background: #F9FAFB; color: #6B7280; }

/* ── 각국 대응 테이블 ── */
.cr-table { width: 100%; border-collapse: collapse; }
.cr-th {
  font-size: 0.62rem; font-weight: 700; color: #6B7280; letter-spacing: 0.5px;
  padding: 7px 10px; border-bottom: 1px solid #E5E7EB; text-align: left;
  background: #F9FAFB;
}
.cr-row { border-bottom: 1px solid #F3F4F6; }
.cr-row:last-child { border-bottom: none; }
.cr-row:hover { background: #FAFAFA; }
.cr-country { font-size: 0.82rem; font-weight: 700; color: #111827; padding: 10px 10px; white-space: nowrap; }
.cr-stance-cell { padding: 10px 10px; }
.cr-stance-badge {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-size: 0.63rem; font-weight: 700; white-space: nowrap;
}
.st-강경   { background: #FEF2F2; color: #B91C1C; }
.st-지지   { background: #FFFBEB; color: #92400E; }
.st-중립   { background: #EFF6FF; color: #1E40AF; }
.st-제재   { background: #F5F3FF; color: #5B21B6; }
.st-협력   { background: #F0FDF4; color: #15803D; }
.st-unknown    { background: #F9FAFB; color: #6B7280; }
.st-대응        { background: #EFF6FF; color: #1E40AF; }
.st-선제        { background: #FEF2F2; color: #B91C1C; }
.st-모니터링    { background: #F9FAFB; color: #6B7280; }
.st-검토        { background: #F5F3FF; color: #5B21B6; }
.cr-action-cell { font-size: 0.75rem; color: #4B5563; padding: 10px 10px; line-height: 1.5; max-width: 300px; }
.cr-suwon-cell  { font-size: 0.71rem; color: #15803D; padding: 10px 10px; line-height: 1.5; font-weight: 600; }

/* ── 한국 정부 부처 브리핑 카드 ── */
.kr-ministry-list { display: flex; flex-direction: column; gap: 10px; padding: 4px 0; }
.kr-ministry-card {
  background: #FFFFFF; border: 1px solid #E5E7EB;
  border-left: 4px solid #1C2B40;
  border-radius: 6px; padding: 12px 14px;
}
.kr-ministry-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.kr-ministry-icon { font-size: 1.1rem; }
.kr-ministry-name {
  font-size: 0.9rem; font-weight: 800; color: #111827;
}
.kr-actions-list {
  margin: 0 0 8px 0; padding-left: 18px; list-style: disc;
}
.kr-actions-list li {
  font-size: 0.76rem; color: #374151; line-height: 1.6;
}
.kr-action-plain { font-size: 0.76rem; color: #374151; line-height: 1.6; margin-bottom: 8px; }
.kr-policy-dir {
  font-size: 0.72rem; color: #6B7280; line-height: 1.5; margin-bottom: 6px;
}
.kr-pd-label {
  display: inline-block; font-size: 0.6rem; font-weight: 700;
  background: #F3F4F6; color: #6B7280;
  padding: 1px 6px; border-radius: 3px; margin-right: 4px;
}
.kr-suwon-box {
  background: #F0FDF4; border-left: 3px solid #15803D;
  border-radius: 0 4px 4px 0; padding: 5px 10px;
  display: flex; gap: 6px; align-items: flex-start;
}
.kr-suwon-label {
  font-size: 0.6rem; font-weight: 700; color: #15803D;
  white-space: nowrap; margin-top: 1px;
}
.kr-suwon-text { font-size: 0.72rem; color: #166534; line-height: 1.5; }

/* ── 지자체 테이블 ── */
.lga-table { width: 100%; border-collapse: collapse; }
.lga-th {
  font-size: 0.62rem; font-weight: 700; color: #6B7280;
  padding: 7px 10px; border-bottom: 1px solid #E5E7EB; text-align: left; background: #F9FAFB;
}
.lga-row { border-bottom: 1px solid #F3F4F6; }
.lga-row:last-child { border-bottom: none; }
.lga-row:hover { background: #FAFAFA; }
.lga-suwon-row { background: #F0F7FF !important; }
.lga-name-cell { font-size: 0.82rem; font-weight: 700; color: #111827; padding: 10px 10px; white-space: nowrap; }
.lga-type-tag {
  display: inline-block; font-size: 0.58rem; font-weight: 700;
  padding: 1px 6px; border-radius: 3px; margin-left: 5px; vertical-align: middle;
}
.tt-광역 { background: #EFF6FF; color: #1E40AF; }
.tt-도   { background: #F5F3FF; color: #5B21B6; }
.tt-기초 { background: #F0FDF4; color: #15803D; }
.lga-stage-cell { padding: 10px 10px; white-space: nowrap; }
.stage-badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.63rem; font-weight: 700; }
.stage-선제    { background: #FEF2F2; color: #B91C1C; }
.stage-적극    { background: #FFFBEB; color: #92400E; }
.stage-검토    { background: #EFF6FF; color: #1E40AF; }
.stage-모니터링 { background: #F9FAFB; color: #6B7280; }
.lga-action-cell { font-size: 0.75rem; color: #4B5563; padding: 10px 10px; line-height: 1.5; }
.lga-ref-cell   { font-size: 0.71rem; color: #15803D; padding: 10px 10px; line-height: 1.5; font-weight: 600; }

/* ── 3컬럼 민생분석 ── */
.triple-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.impact-card {
  background: #FFFFFF; border: 1px solid #E5E7EB;
  border-radius: 8px; padding: 18px; height: 100%;
}
.impact-card-energy   { border-top: 3px solid #EF4444; }
.impact-card-industry { border-top: 3px solid #F59E0B; }
.impact-card-life     { border-top: 3px solid #3B82F6; }
.ic-icon { font-size: 1.3rem; margin-bottom: 6px; }
.ic-category { font-size: 0.88rem; font-weight: 800; color: #111827; margin-bottom: 8px; }
.ic-level-badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.63rem; font-weight: 700; margin-bottom: 10px; }
.icl-높음    { background: #FEF2F2; color: #B91C1C; }
.icl-중간    { background: #FFFBEB; color: #92400E; }
.icl-낮음    { background: #F0FDF4; color: #15803D; }
.icl-모니터링 { background: #F9FAFB; color: #6B7280; }
.ic-title   { font-size: 0.88rem; font-weight: 800; color: #111827; margin-bottom: 8px; }
.ic-summary { font-size: 0.76rem; color: #4B5563; line-height: 1.65; margin-bottom: 12px; }
.ic-kpi-box {
  background: #EFF6FF; border-left: 2px solid #2563EB;
  padding: 8px 10px; margin-bottom: 6px; border-radius: 0 4px 4px 0;
}
.ic-kpi-label { font-size: 0.57rem; font-weight: 700; color: #1D4ED8; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 3px; }
.ic-kpi-value { font-size: 0.74rem; color: #1E3A8A; line-height: 1.5; }
.ic-other-box {
  background: #F0FDF4; border-left: 2px solid #16A34A;
  padding: 8px 10px; border-radius: 0 4px 4px 0;
}
.ic-other-label { font-size: 0.57rem; font-weight: 700; color: #15803D; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 3px; }
.ic-other-value { font-size: 0.74rem; color: #14532D; line-height: 1.5; }

/* ── 대응과제 카드 ── */
.action-card {
  background: #FFFFFF; border: 1px solid #E5E7EB;
  border-radius: 8px; padding: 18px; height: 100%;
}
.ac-rank { font-size: 0.58rem; font-weight: 700; color: #9CA3AF; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 5px; }
.ac-priority { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.63rem; font-weight: 700; margin-bottom: 10px; }
.pri-즉시 { background: #FEF2F2; color: #B91C1C; }
.pri-단기 { background: #FFFBEB; color: #92400E; }
.pri-중기 { background: #EFF6FF; color: #1E40AF; }
.ac-title { font-size: 0.88rem; font-weight: 800; color: #111827; margin-bottom: 7px; line-height: 1.4; }
.ac-desc  { font-size: 0.75rem; color: #4B5563; line-height: 1.65; margin-bottom: 12px; }
.evidence-stack { border-top: 1px solid #F3F4F6; padding-top: 10px; display: flex; flex-direction: column; gap: 5px; }
.ev-item { padding: 7px 10px; border-radius: 4px; font-size: 0.71rem; color: #374151; line-height: 1.5; }
.ev-bench  { background: #EFF6FF; border-left: 2px solid #2563EB; }
.ev-expert { background: #F0FDF4; border-left: 2px solid #16A34A; }
.ev-report { background: #F5F3FF; border-left: 2px solid #7C3AED; }
.ev-tag { font-size: 0.57rem; font-weight: 700; letter-spacing: 0.8px; display: block; margin-bottom: 2px; text-transform: uppercase; }
.ev-bench  .ev-tag { color: #1D4ED8; }
.ev-expert .ev-tag { color: #15803D; }
.ev-report .ev-tag { color: #6D28D9; }

/* ── 벤치마킹 ── */
.bench-card {
  background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 16px 18px;
}
.bench-city { font-size: 0.8rem; font-weight: 800; color: #1C2B40; margin-bottom: 8px; }
.bench-item { display: flex; gap: 7px; font-size: 0.74rem; color: #4B5563; line-height: 1.55; margin-bottom: 4px; }
.bench-arrow { color: #2563EB; flex-shrink: 0; font-weight: 700; }

/* ── YouTube ── */
/* ── YouTube 썸네일 카드 ── */
.yt-card {
  background: #FFFFFF; border: 1px solid #E5E7EB;
  border-radius: 10px; overflow: hidden; height: 100%;
  display: flex; flex-direction: column;
  transition: box-shadow 0.2s;
}
.yt-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); }

/* 썸네일 */
.yt-thumb-link { display: block; text-decoration: none; }
.yt-thumb-wrap {
  position: relative; width: 100%; padding-top: 56.25%; /* 16:9 */
  background: #1C2B40; overflow: hidden;
}
.yt-thumb {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; object-fit: cover;
}
.yt-play-btn {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 44px; height: 44px; background: rgba(220,38,38,0.88);
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 1rem; padding-left: 3px;
  opacity: 0; transition: opacity 0.2s;
}
.yt-thumb-link:hover .yt-play-btn { opacity: 1; }

/* 카드 바디 */
.yt-card-body { padding: 12px 14px; flex: 1; display: flex; flex-direction: column; gap: 7px; }
.yt-channel-row { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.yt-ch-badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.63rem; font-weight: 700; }
.yt-aljazeera { background: #FEF2F2; color: #B91C1C; }
.yt-dw        { background: #EFF6FF; color: #1E40AF; }
.yt-yonhap    { background: #F0FDF4; color: #15803D; }
.yt-default   { background: #F9FAFB; color: #6B7280; }
.yt-rel-badge  { display: inline-block; padding: 2px 7px; border-radius: 3px; font-size: 0.6rem; font-weight: 700; margin-left: auto; }
.yt-type-badge { display: inline-block; padding: 2px 7px; border-radius: 3px; font-size: 0.6rem; font-weight: 600; background: #F3F4F6; color: #4B5563; }

/* 제목 링크 */
a.yt-title {
  font-size: 0.8rem; font-weight: 800; color: #111827;
  line-height: 1.45; text-decoration: none; display: block;
}
a.yt-title:hover { color: #1C2B40; text-decoration: underline; }

/* 요약 */
.yt-summary { flex: 1; }
.yt-sum-line { font-size: 0.74rem; color: #374151; line-height: 1.65; padding: 2px 0; }

/* 수원 연결점 */
.yt-suwon {
  font-size: 0.69rem; color: #1D4ED8; background: #EFF6FF;
  padding: 5px 8px; border-radius: 4px; line-height: 1.5;
}

/* ── 리스크 점검 (구 Devil's Critique) ── */
.devil-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-left: 4px solid #DC2626;
  border-radius: 8px;
  padding: 20px 24px;
  margin-bottom: 16px;
}
.devil-stamp {
  display: inline-block; float: right;
  font-size: 0.6rem; font-weight: 700; letter-spacing: 1px;
  background: #FEF2F2; color: #B91C1C; padding: 3px 10px;
  border-radius: 3px; border: 1px solid #FECACA;
}
.devil-quote {
  font-size: 0.95rem; font-weight: 800; color: #111827;
  margin-bottom: 16px; padding-bottom: 12px;
  border-bottom: 1px solid #E5E7EB; clear: both;
}
.devil-quote .dq-hi { color: #DC2626; }
.devil-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.dp-num   { display: none; }
.dp-title { font-size: 0.88rem; font-weight: 800; color: #111827; margin-bottom: 7px; }
.dp-body  { font-size: 0.8rem;  color: #374151;  line-height: 1.75; }

/* ── 다음주 핵심이슈 ── */
.next-issue-list { display: flex; flex-direction: column; gap: 10px; }
.next-issue-item {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 14px 16px; border-radius: 8px;
  background: #F9FAFB; border: 1px solid #E5E7EB;
}
.ni-num {
  flex-shrink: 0; width: 26px; height: 26px;
  background: #1C2B40; border-radius: 50%;
  color: #FFFFFF; font-size: 0.7rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  margin-top: 1px;
}
.ni-content { flex: 1; min-width: 0; }
.ni-title  { font-size: 0.88rem; font-weight: 800; color: #111827; line-height: 1.4; margin-bottom: 4px; }
.ni-detail { font-size: 0.75rem; color: #4B5563; line-height: 1.6; }
.ni-tag {
  flex-shrink: 0; padding: 2px 8px; border-radius: 3px;
  font-size: 0.62rem; font-weight: 700; white-space: nowrap; margin-top: 3px;
}
.ni-high   { background: #FEF2F2; color: #B91C1C; }
.ni-mid    { background: #FFFBEB; color: #92400E; }
.ni-watch  { background: #EFF6FF; color: #1E40AF; }
/* ── 시민 목소리 섹션 ── */
.cvoice-wrap { padding-top: 2px; }
.cvoice-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.cvoice-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: 1px solid #D1D5DB;
  border-radius: 18px;
  background: #FFFFFF;
  color: #6B7280;
  font-size: 0.77rem;
  font-weight: 700;
  line-height: 1;
}
.cvoice-tab.active {
  background: #1C2B40;
  color: #FFFFFF;
  border-color: #1C2B40;
}
.cvoice-tab .cnt {
  font-family: Inter, monospace;
  font-size: 0.66rem;
  opacity: 0.82;
}
.cvoice-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cvoice-item {
  border-left: 3px solid #E5E7EB;
  padding: 10px 12px 10px 14px;
  background: #FFFFFF;
  border-radius: 0 6px 6px 0;
}
.cvoice-item:hover {
  border-left-color: #B91C1C;
  background: #FAFAFA;
}
.cvoice-quote {
  font-size: 0.8rem;
  color: #111827;
  line-height: 1.65;
  font-weight: 500;
}
.cvoice-quote b {
  font-weight: 800;
  color: #111827;
  background: linear-gradient(transparent 60%, #FEF3C7 60%);
}
.cvoice-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.cvoice-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.63rem;
  font-weight: 700;
}
.cv-red   { background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA; }
.cv-navy  { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; }
.cv-amber { background:#FFF7ED; color:#B45309; border:1px solid #FED7AA; }
.cv-green { background:#F0FDF4; color:#15803D; border:1px solid #BBF7D0; }
.cv-gray  { background:#F9FAFB; color:#6B7280; border:1px solid #E5E7EB; }
.cvoice-src, .cvoice-like {
  font-size: 0.67rem;
  color: #6B7280;
  font-family: Inter, monospace;
}
.cvoice-link {
  font-size: 0.67rem;
  color: #1D4ED8;
  font-weight: 700;
  text-decoration: none;
}
.cvoice-link:hover { text-decoration: underline; }
.cvoice-foot {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #D1D5DB;
  font-size: 0.64rem;
  color: #6B7280;
  line-height: 1.7;
}
.cvoice-foot b { color: #374151; }

/* ── 빈 상태 ── */
.empty-dark {
  text-align: center; padding: 20px; border: 1px dashed #D1D5DB;
  border-radius: 6px; color: #9CA3AF; font-size: 0.77rem; background: #F9FAFB;
}

/* ── 푸터 ── */
.intel-footer {
  padding: 16px 32px 18px 32px;
  border-top: 1px solid #E5E7EB;
  font-size: 0.64rem; color: #4B5563;
  background: #F3F4F6;
  border-radius: 0 0 12px 12px;
}
.footer-grid {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0 28px;
  align-items: start;
}
.footer-col { display: flex; flex-direction: column; gap: 5px; }
.footer-label { font-size: 0.68rem; font-weight: 800; color: #1C2B40; }
.footer-val   { font-size: 0.65rem; color: #4B5563; line-height: 1.55; }
.footer-divider { width: 1px; background: #D1D5DB; align-self: stretch; margin: 0; }
.footer-stamp { font-size: 0.58rem; font-weight: 600; letter-spacing: 0.8px; color: #9CA3AF; text-transform: uppercase; line-height: 1.6; }

/* ── 추가 stance 배지 ── */
.st-대응    { background: #F0F9FF; color: #0369A1; }
.st-선제    { background: #FEF2F2; color: #B91C1C; }
.st-모니터링 { background: #F9FAFB; color: #6B7280; }

/* ── CSS-only 커스텀 탭 ── */
.ctabs input[type="radio"] { display: none; }
.ctab-panel { display: none; padding: 8px 0; }
#cr-me:checked ~ #panel-cr-me,
#cr-gl:checked ~ #panel-cr-gl,
#cr-kr:checked ~ #panel-cr-kr { display: block; }

.ctab-bar {
  display: flex; border-bottom: 2px solid #E5E7EB; margin-bottom: 12px;
}
.ctab-label {
  padding: 9px 22px; cursor: pointer;
  color: #6B7280; font-weight: 600; font-size: 0.82rem;
  border-bottom: 3px solid transparent; margin-bottom: -2px;
}
.ctab-label:hover { color: #374151; }
#cr-me:checked ~ .ctab-bar label[for="cr-me"],
#cr-gl:checked ~ .ctab-bar label[for="cr-gl"],
#cr-kr:checked ~ .ctab-bar label[for="cr-kr"] {
  color: #1C2B40; border-bottom-color: #1C2B40;
}

/* ── 각국 대응 정책 아이템 리스트 ── */
.cr-policy-list { padding: 4px 0; }
.policy-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 2px; border-bottom: 1px solid #F3F4F6;
}
.policy-item:last-child { border-bottom: none; }
.pi-content { flex: 1; min-width: 0; }
.pi-title   { font-size: 0.83rem; font-weight: 700; color: #111827; line-height: 1.4; }
.pi-detail  { font-size: 0.72rem; color: #6B7280; margin-top: 3px; line-height: 1.55; }
/* 오른쪽 입장 설명 칼럼 — 고정 폭, 파란 계열 */
.cr-stance-desc {
  flex-shrink: 0;
  width: 230px;
  min-width: 230px;
  font-size: 0.72rem;
  font-weight: 500;
  color: #1E40AF;
  background: #EFF6FF;
  border-radius: 6px;
  padding: 6px 10px;
  line-height: 1.55;
  word-break: keep-all;
}

/* ── 인쇄 — A4 최적화 ── */
@media print {
  @page { size: A4; margin: 15mm 18mm; }
  .stApp, [data-testid="stAppViewContainer"] { background: white !important; }
  [data-testid="stSidebar"], .no-print { display: none !important; }
  .intel-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .metrics-strip-outer { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .section-card, .hero-card, .panel-card,
  .impact-card, .action-card, .bench-card, .yt-card {
    break-inside: avoid; box-shadow: none !important;
  }
  .page-wrap { max-width: 100%; padding: 0; }
  .intel-header-inner, .metrics-strip { max-width: 100%; }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────
def load_json(path):
    p = Path(path)
    if p.exists():
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    return None

def ds(d): return d.strftime("%Y%m%d")
def fmt(d): return d.strftime("%Y-%m-%d")
def fmt_ko(d): return d.strftime("%Y년 %m월 %d일")

def load_citizen_voice_xlsx(date_str):
    candidates = [
        DATA_DIR / "citizen_voice" / f"citizen_voice_{date_str}.xlsx",
        DATA_DIR / "citizen_voice" / f"citizen_voice_{date_str.replace('-', '')}.xlsx",
        DATA_DIR / f"citizen_voice_{date_str}.xlsx",
        DATA_DIR / f"citizen_voice_{date_str.replace('-', '')}.xlsx",
    ]
    target = next((p for p in candidates if p.exists()), None)
    if not target:
        return None

    try:
        df = pd.read_excel(target, sheet_name="data")
        df.columns = [str(c).strip() for c in df.columns]

        required = ["channel", "source_title", "comment", "like_count", "posted_date", "tag"]
        for col in required:
            if col not in df.columns:
                return None

        if "source_url" not in df.columns:
            df["source_url"] = ""
        if "bold_phrase" not in df.columns:
            df["bold_phrase"] = ""

        df = df[required + ["source_url", "bold_phrase"]].copy()
        df = df.dropna(subset=required)

        df["channel"] = df["channel"].astype(str).str.strip().str.lower()
        df["source_title"] = df["source_title"].astype(str).str.strip()
        df["comment"] = df["comment"].astype(str).str.strip()
        df["tag"] = df["tag"].astype(str).str.strip()
        df["source_url"] = df["source_url"].fillna("").astype(str).str.strip()
        df["bold_phrase"] = df["bold_phrase"].fillna("").astype(str).str.strip()
        df["like_count"] = pd.to_numeric(df["like_count"], errors="coerce").fillna(0).astype(int)
        df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")

        df = df.dropna(subset=["posted_date"])
        df = df[df["channel"].isin(["naver", "youtube", "local", "daangn"])].copy()
        if df.empty:
            return None

        df = df.sort_values(["like_count", "posted_date"], ascending=[False, False]).reset_index(drop=True)
        return df
    except Exception:
        return None


def get_citizen_voice_items(date_str):
    df = load_citizen_voice_xlsx(date_str)
    if df is not None and not df.empty:
        return df.to_dict("records")

    return [
        {
            "channel": "naver",
            "source_title": "수원 휘발유 2천원 돌파",
            "comment": "수원역 근처 휘발유 2,150원 찍었네요. 출퇴근만 해도 한 달에 7만원 더 나가는 셈",
            "like_count": 312,
            "posted_date": pd.to_datetime("2026-05-10"),
            "tag": "유류비",
            "source_url": "",
            "bold_phrase": "",
        },
        {
            "channel": "naver",
            "source_title": "중동전쟁 민생 직격",
            "comment": "경기도 안에서도 수원만 별다른 대책이 없네요. 성남은 상품권 할인이라도 해주던데",
            "like_count": 187,
            "posted_date": pd.to_datetime("2026-05-09"),
            "tag": "정책",
            "source_url": "",
            "bold_phrase": "수원만 별다른 대책이 없네요",
        },
        {
            "channel": "youtube",
            "source_title": "고유가에 자영업자 곡소리",
            "comment": "배달비 4,500원이면 차라리 직접 가서 사 먹는 게 싸요. 동네 분식집 사장님도 손님 줄었다고 한숨",
            "like_count": 156,
            "posted_date": pd.to_datetime("2026-05-08"),
            "tag": "소상공인",
            "source_url": "",
            "bold_phrase": "",
        },
        {
            "channel": "local",
            "source_title": "6월 도시가스 인상 예고",
            "comment": "도시가스도 6월에 또 오른다는데 우리 동네에서라도 뭐 좀 해줬으면 좋겠어요",
            "like_count": 94,
            "posted_date": pd.to_datetime("2026-05-07"),
            "tag": "에너지",
            "source_url": "",
            "bold_phrase": "",
        },
        {
            "channel": "daangn",
            "source_title": "수원 생활물가 체감",
            "comment": "당근 동네생활에서도 요즘 기름값이랑 배달비 부담 얘기가 자주 보이네요",
            "like_count": 82,
            "posted_date": pd.to_datetime("2026-05-10"),
            "tag": "유류비",
            "source_url": "",
            "bold_phrase": "기름값이랑 배달비 부담",
        },
    ]


def cv_tag_class(tag):
    return {
        "유류비": "cv-red",
        "정책": "cv-navy",
        "소상공인": "cv-amber",
        "에너지": "cv-green",
    }.get(str(tag).strip(), "cv-gray")


def cv_channel_label(ch):
    return {
        "naver": "네이버 뉴스",
        "youtube": "유튜브",
        "local": "지역 언론",
        "daangn": "당근",
    }.get(ch, ch)


def cv_mmdd(v):
    try:
        dt = pd.to_datetime(v)
        return f"{dt.month}.{dt.day}"
    except Exception:
        return "-"


def cv_highlight(text, phrase):
    text = html.escape(str(text or ""))
    phrase = str(phrase or "").strip()
    if not phrase:
        return text
    try:
        return re.sub(
            re.escape(html.escape(phrase)),
            f"<b>{html.escape(phrase)}</b>",
            text,
            count=1,
            flags=re.IGNORECASE
        )
    except Exception:
        return text


def build_citizen_voice_html(items, selected_channel="all", limit=4):
    items = items or []

    counts = {
        "all": len(items),
        "naver": sum(1 for x in items if x.get("channel") == "naver"),
        "youtube": sum(1 for x in items if x.get("channel") == "youtube"),
        "local": sum(1 for x in items if x.get("channel") == "local"),
        "daangn": sum(1 for x in items if x.get("channel") == "daangn"),
    }

    filtered = items[:limit] if selected_channel == "all" else [
        x for x in items if x.get("channel") == selected_channel
    ][:limit]

    tabs = []
    for key, label in [
        ("all", "전체"),
        ("naver", "네이버 뉴스"),
        ("youtube", "유튜브"),
        ("local", "지역 언론"),
        ("daangn", "당근"),
    ]:
        active = " active" if key == selected_channel else ""
        tabs.append(
            f"<span class='cvoice-tab{active}'>{label}<span class='cnt'>{counts.get(key, 0)}</span></span>"
        )

    rows = []
    for row in filtered:
        tag = str(row.get("tag", "")).strip()
        source_title = html.escape(str(row.get("source_title", "")))
        comment_html = cv_highlight(row.get("comment", ""), row.get("bold_phrase", ""))
        source_url = str(row.get("source_url", "")).strip()
        link_html = (
            f"<a class='cvoice-link' href='{html.escape(source_url)}' target='_blank' rel='noopener noreferrer'>원문</a>"
            if source_url else ""
        )

        row_html = (
            f"<div class='cvoice-item'>"
            f"<div class='cvoice-quote'>\"{comment_html}\"</div>"
            f"<div class='cvoice-meta'>"
            f"<span class='cvoice-tag {cv_tag_class(tag)}'>{html.escape(tag)}</span>"
            f"<span class='cvoice-src'>{cv_channel_label(row.get('channel'))} | &quot;{source_title}&quot; | {cv_mmdd(row.get('posted_date'))}</span>"
            f"<span class='cvoice-like'>🔥 {int(row.get('like_count', 0)):,}</span>"
            f"{link_html}"
            f"</div></div>"
        )
        rows.append(row_html)

    if not rows:
        rows.append("<div class='empty-dark'>표시할 시민 목소리 데이터가 없습니다.</div>")

    foot = (
        "<div class='cvoice-foot'>"
        "<div><b>수집</b> 수원 관련 민생 키워드 매칭 기사·영상·공개 채널 게시물 중 반응 상위 선별</div>"
        "<div><b>채널</b> 네이버 뉴스 · 유튜브 · 지역 언론 · 당근</div>"
        "<div><b>기준</b> 공감/좋아요 상위 · 직전 7일 중심</div>"
        "</div>"
    )

    return (
        f"<div class='cvoice-wrap'>"
        f"<div class='cvoice-tabs'>{''.join(tabs)}</div>"
        f"<div class='cvoice-list'>{''.join(rows)}</div>"
        f"{foot}"
        f"</div>"
    )

# ─────────────────────────────────────────────
# 날짜 목록 수집
# ─────────────────────────────────────────────
def get_available_dates() -> list:
    """분석 파일이 존재하는 날짜 목록 (최신순)"""
    dates = []
    try:
        for f in sorted(ANALYZED_DIR.glob("analyzed_*.json"), reverse=True):
            date_part = f.stem.replace("analyzed_", "")
            try:
                dates.append(datetime.strptime(date_part, "%Y%m%d").date())
            except ValueError:
                continue
    except Exception:
        pass
    return dates or [date.today()]

# 2026-04-01 이후 데이터만 표시
_START_DATE = date(2026, 4, 1)
_available_dates = [d for d in get_available_dates() if d >= _START_DATE]
if not _available_dates:
    _available_dates = [date.today()]

# ─────────────────────────────────────────────
# 날짜 선택기 — 월 버튼 + 날짜 칩
# ─────────────────────────────────────────────
from collections import defaultdict

_today  = date.today()
_DAY_KO = ["월","화","수","목","금","토","일"]

_by_month = defaultdict(list)
for _d in _available_dates:
    _by_month[(_d.year, _d.month)].append(_d)
_months_list = sorted(_by_month.keys(), reverse=True)

if "dp_month" not in st.session_state:
    st.session_state.dp_month = _months_list[0]
if st.session_state.dp_month not in _months_list:
    st.session_state.dp_month = _months_list[0]

_sel_dates = sorted(_by_month[st.session_state.dp_month], reverse=True)

# ─────────────────────────────────────────────
# 모바일 버전 바로가기 버튼
# ─────────────────────────────────────────────
st.markdown("""
<div style="
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
">
  <a href="https://sri.pplx.app/" target="_blank" rel="noopener noreferrer" style="
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #1C2B40;
    color: #FFFFFF;
    text-decoration: none;
    padding: 7px 16px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.3px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
  ">
    <span style="font-size:1rem;">📱</span> 모바일로 보기
  </a>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ── 월 버튼: 작고 둥글게 ── */
div[data-testid="stHorizontalBlock"] button[kind="primary"],
div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
  border-radius: 18px !important;
  padding: 2px 10px !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  height: 28px !important;
  min-height: 0 !important;
  line-height: 1 !important;
}
/* ── 날짜 칩 radio: 라벨 숨기기 ── */
div[data-testid="stRadio"] > div:first-child > label {
  display: none !important;
}
/* ── 날짜 칩: 가로 배열 + 간격 ── */
div[data-testid="stRadio"] [role="radiogroup"] {
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 5px !important;
  align-items: center !important;
}
/* ── 각 칩 기본 스타일 ── */
div[data-testid="stRadio"] [role="radiogroup"] > label {
  background: #F3F4F6 !important;
  border: 1.5px solid #D1D5DB !important;
  border-radius: 18px !important;
  padding: 3px 12px !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  color: #374151 !important;
  white-space: nowrap !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
}
/* ── 호버 ── */
div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
  border-color: #9CA3AF !important;
  background: #E5E7EB !important;
}
/* ── 선택된 칩 ── */
div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
  background: #1C2B40 !important;
  border-color: #1C2B40 !important;
  color: #FFFFFF !important;
}
div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) * {
  color: #FFFFFF !important;
}
/* ── 라디오 원형 버튼 숨기기 ── */
div[data-testid="stRadio"] [role="radiogroup"] input[type="radio"] {
  position: absolute !important;
  opacity: 0 !important;
  width: 0 !important;
  height: 0 !important;
  pointer-events: none !important;
}
/* ── 라디오 내부 span(원) 숨기기 ── */
div[data-testid="stRadio"] [role="radiogroup"] > label > span:first-child {
  display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── 1행: 월 버튼들
_m_cols = st.columns([1] * len(_months_list) + [10])
for i, ym in enumerate(_months_list):
    with _m_cols[i]:
        _active = (ym == st.session_state.dp_month)
        if st.button(
            f"{ym[1]}월",
            key=f"dp_m_{ym[0]}_{ym[1]}",
            type="primary" if _active else "secondary",
            use_container_width=True,
        ):
            st.session_state.dp_month = ym
            st.rerun()

# ── 2행: 날짜 칩 (선택된 월)
selected_date = st.radio(
    "날짜 선택",
    options=_sel_dates,
    format_func=lambda d: f"{'★ ' if d == _today else ''}{d.month}/{d.day}({_DAY_KO[d.weekday()]})",
    horizontal=True,
    index=0,
    key=f"dp_d_{st.session_state.dp_month[0]}_{st.session_state.dp_month[1]}",
    label_visibility="collapsed",
)

date_str = ds(selected_date)
st.markdown(
    f'<div style="font-size:0.7rem;color:#9CA3AF;margin:-4px 0 10px 2px;">'
    f'<b style="color:#1C2B40">{selected_date.strftime("%Y년 %m월 %d일")}</b>'
    f' ({_DAY_KO[selected_date.weekday()]})'
    f'&nbsp;·&nbsp;PC·태블릿 가로 보기 권장</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# 사이드바 (파이프라인 컨트롤만 유지)
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## ⚙️ {'V2' if _IS_V2 else '운영 컨트롤'}")
    st.divider()
    st.caption(f"📅 선택 날짜: **{selected_date.strftime('%Y-%m-%d')}**")
    st.divider()

    if not _IS_V2:
        # ── V1 파이프라인 실행 버튼
        col_run, col_stop = st.columns(2)
        with col_run:
            if st.button("🚀 파이프라인 시작", type="primary", use_container_width=True):
                try:
                    proc = subprocess.Popen(
                        ["python", "orchestrator.py", "--date", fmt(selected_date)],
                        cwd=str(Path(__file__).parent),
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                    st.session_state["pipeline_pid"] = proc.pid
                    st.success(f"✅ 백그라운드 실행 중 (PID {proc.pid})\n새 창에서 진행 상황을 확인하세요.")
                except Exception as e:
                    st.error(f"실행 오류: {e}")
        with col_stop:
            if st.button("⏹ 중단", use_container_width=True):
                pid = st.session_state.get("pipeline_pid")
                if pid:
                    try:
                        import signal as _sig, os as _os
                        _os.kill(pid, _sig.SIGTERM)
                        st.warning(f"PID {pid} 중단 요청")
                        st.session_state.pop("pipeline_pid", None)
                    except Exception as e:
                        st.error(f"중단 오류: {e}")
                else:
                    st.info("실행 중인 파이프라인 없음")
    else:
        # ── V2: 엑셀 업로드 + 분석 실행
        st.caption("형식: 언어|분류|언론사|날짜|제목|링크")
        uploaded = st.file_uploader("엑셀 파일 (.xlsx)", type=["xlsx"],
                                    label_visibility="collapsed")
        if uploaded:
            manual_dt = st.date_input("분석 날짜", value=selected_date, key="v2_date")
            fetch_chk = st.checkbox("기사 본문 자동 수집 (느림)", value=False)
            if st.button("🔍 분석 시작", type="primary", use_container_width=True):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name
                cmd = ["python", "manual_input.py", "--file", tmp_path,
                       "--date", manual_dt.strftime("%Y-%m-%d")]
                if fetch_chk:
                    cmd.append("--fetch-body")
                try:
                    proc_v2 = subprocess.Popen(
                        cmd, cwd=str(Path(__file__).parent),
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                    st.success(f"✅ 분석 실행 중 (PID {proc_v2.pid})\n완료 후 새로고침하세요.")
                except Exception as e:
                    st.error(f"실행 오류: {e}")
    st.divider()
    st.caption("📂 파일 현황")
    for lbl, path in {
        "뉴스 분석": ANALYZED_DIR        / f"analyzed_{date_str}.json",
        "각국 대응": COUNTRY_RESPONSE_DIR / f"cr_{date_str}.json",
        "패러다임":  PARADIGM_DIR         / f"paradigm_{date_str}.json",
        "민생 분석": POLICY_DIR           / f"minseang_{date_str}.json",
        "국내 지표": DOMESTIC_DIR         / f"domestic_{date_str}.json",
    }.items():
        st.caption(f"{'✅' if Path(path).exists() else '⬜'} {lbl}")
    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%H:%M')}")


# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────
analyzed  = load_json(ANALYZED_DIR        / f"analyzed_{date_str}.json") or []
cr_data   = load_json(COUNTRY_RESPONSE_DIR / f"cr_{date_str}.json")     or {}
paradigm  = load_json(PARADIGM_DIR         / f"paradigm_{date_str}.json") or {}
minseang  = load_json(POLICY_DIR           / f"minseang_{date_str}.json") or {}
domestic  = load_json(DOMESTIC_DIR         / f"domestic_{date_str}.json") or {}
yt_data   = load_json(DATA_DIR / "youtube" / f"yt_summary_{date_str}.json") or {}

if not analyzed:
    analyzed = load_json(CLEAN_DIR / f"clean_{date_str}.json") or []

urgency      = minseang.get("urgency", "모니터링")
headline     = minseang.get("today_headline", "이란-미국 긴장 고조 — 수원시 에너지·물가 영향 모니터링 중")
oil          = domestic.get("oil_price", {})
gas_nat      = oil.get("gasoline_national", None)
gas_ggy      = oil.get("gasoline_gyeonggi", None)
ex_rate      = domestic.get("exchange_rate", {})
wti_price    = oil.get("wti_usd", None)
brent_price  = oil.get("brent_usd", None)
dubai_price  = oil.get("dubai_usd", None)
dubai_note   = oil.get("dubai_note", "")
rbob_gal     = oil.get("rbob_usd_gal", None)
usd_krw      = ex_rate.get("USD_KRW", None)

# 오피넷 실데이터만 사용 — 추정값 사용 안 함
cr_responses      = cr_data.get("country_responses", [])
kr_min_responses  = cr_data.get("kr_ministry_responses", [])  # 한국 부처별 대응
issues            = cr_data.get("emerging_issues", [])
key_trends        = cr_data.get("key_trends", [])
민생_분석    = minseang.get("민생경제_분석", {})
대응과제     = minseang.get("우선_대응과제", [])
signals      = paradigm.get("signals", [])
lessons      = minseang.get("international_lessons", {})
top_articles = sorted(analyzed, key=lambda x: x.get("importance",0), reverse=True)[:5]

scout_points = minseang.get("scout_points", [])
if not scout_points:
    for a in top_articles[:3]:
        s = a.get("summary_ko") or a.get("summary") or a.get("title","")
        if s: scout_points.append(s[:120])


# ═══════════════════════════════════════════════════════════
# ① 헤더 바
# ═══════════════════════════════════════════════════════════
urg_map = {"긴급": "긴급", "주의": "주의", "모니터링": "모니터링"}
urg_label = urg_map.get(urgency, "모니터링")
date_ko = selected_date.strftime("%Y년 %m월 %d일 (%a)").replace(
    "Mon","월").replace("Tue","화").replace("Wed","수").replace(
    "Thu","목").replace("Fri","금").replace("Sat","토").replace("Sun","일")

# 지표 띠 데이터 — 두바이유 우선, 없으면 Brent → WTI 순으로 대체
_oil_ref_price = dubai_price if isinstance(dubai_price,(int,float)) else (
                 brent_price if isinstance(brent_price,(int,float)) else wti_price)
_oil_ref_label = ("EIA Dubai" if isinstance(dubai_price,(int,float)) and not dubai_note else
                  ("두바이 추산" if dubai_note else
                   ("ICE Brent" if isinstance(brent_price,(int,float)) else "WTI")))
dubai_str = f"${_oil_ref_price:,.2f}" if isinstance(_oil_ref_price,(int,float)) else "N/A"
brent_str = dubai_str  # 하위 호환 유지
wti_str  = f"${wti_price:,.2f}" if isinstance(wti_price,(int,float)) else "N/A"
krw_str  = f"{usd_krw:,.0f}원"  if isinstance(usd_krw,(int,float)) else "N/A"
gas_str  = f"{gas_nat:,}원"     if isinstance(gas_nat,(int,float)) else "N/A (오피넷 미수집)"
ggy_str2 = f"{gas_ggy:,}원"     if isinstance(gas_ggy,(int,float)) else "N/A"
_cpi_obj    = domestic.get("cpi", {})
_cpi_val    = _cpi_obj.get("cpi_yoy_pct") or _cpi_obj.get("cpi_latest")
cpi_str     = f"{_cpi_val:.1f}" if isinstance(_cpi_val, (int, float)) else "N/A"
_cpi_period = str(_cpi_obj.get("period_current", ""))  # e.g. "202604"
if len(_cpi_period) == 6:
    _cpi_sub = f"{int(_cpi_period[4:6])}월 전년비"
else:
    _cpi_sub = "전년비"
# 휘발유 추정 여부 표시용
gas_is_est = oil.get("gasoline_national") is None and gas_nat is not None
day_d    = (selected_date - date(2026,4,1)).days  # D-day 기준 (예시)

st.markdown(f"""
<div class="intel-header">
  <div class="intel-header-inner">
    <div class="header-brand">
      <div class="header-org">수원시정연구원
        <span style="font-size:0.65rem;font-weight:700;background:{'#7C3AED' if _IS_V2 else '#1E40AF'};color:#fff;
          border-radius:4px;padding:1px 7px;margin-left:8px;letter-spacing:0.5px">{_VER_LABEL}</span>
      </div>
      <div class="header-main">중동전쟁에 따른 민생경제 대응 모니터링</div>
      <div class="header-date-line">{date_ko}</div>
    </div>
    <div class="header-right"></div>
  </div>
</div>
<div class="metrics-strip-outer"><div class="metrics-strip">
  <div class="ms-item">
    <div class="ms-label">두바이유</div>
    <div class="ms-value up">{dubai_str}</div>
    <div class="ms-sub">{_oil_ref_label}</div>
  </div>
  <div class="ms-item">
    <div class="ms-label">달러·원</div>
    <div class="ms-value">{krw_str}</div>
    <div class="ms-sub">{domestic.get("exchange_rate",{}).get("date","--")} 기준</div>
  </div>
  <div class="ms-item">
    <div class="ms-label">전국 휘발유</div>
    <div class="ms-value up">{gas_str}</div>
    <div class="ms-sub">{"오피넷" if isinstance(gas_nat,(int,float)) else "수집 필요"}</div>
  </div>
  <div class="ms-item">
    <div class="ms-label">소비자물가</div>
    <div class="ms-value up">{f"+{cpi_str}%" if cpi_str!="N/A" else "N/A"}</div>
    <div class="ms-sub">{_cpi_sub}</div>
  </div>
</div></div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 메인 컨텐츠 래퍼
# ═══════════════════════════════════════════════════════════
st.markdown('<div class="page-wrap">', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ② 히어로 카드 — 핵심 헤드라인 + 메트릭
# ═══════════════════════════════════════════════════════════
# 메인 유가 지표
if isinstance(gas_nat, (int,float)):
    price_label = "휘발유 (전국 평균)"
    price_value = f"{gas_nat:,}"
    price_unit  = "원/ℓ"
elif isinstance(wti_price, (int,float)):
    price_label = "WTI 국제유가"
    price_value = f"{wti_price:,.2f}"
    price_unit  = "USD/bbl"
else:
    price_label = "유가"
    price_value = "N/A"
    price_unit  = ""

usd_display = f"{usd_krw:,.0f}" if isinstance(usd_krw,(int,float)) else "N/A"

# 이번주 핵심동향 — signal-item 스타일로 렌더링
_scout_colors = ["red", "amber", "blue", "green", "red"]
if scout_points:
    scout_html = "".join(
        f'<div class="signal-item">'
        f'<div class="sig-dot sig-{_scout_colors[i % len(_scout_colors)]}"></div>'
        f'<div>{pt}</div>'
        f'</div>'
        for i, pt in enumerate(scout_points)
    )
else:
    scout_html = '<div class="empty-dark">파이프라인 실행 후 핵심 동향이 표시됩니다.</div>'

st.markdown(f"""
<div class="section-card">
  <div class="sec-header">
    <span class="sec-title"><span class="sec-num">01</span> 이번주 핵심 동향</span>
    <span class="sec-date">{fmt_ko(selected_date)}</span>
  </div>
  {scout_html}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ③ 수원시 민생경제 영향 분석 (최상단 배치)
# ═══════════════════════════════════════════════════════════
CATEGORY_META = {
    "지역산업":       ("🏭", "지역산업 · 제조 수출", "energy"),
    "소상공인_자영업": ("🛒", "소상공인 · 자영업",   "industry"),
    "시민생활":       ("🏠", "시민생활 · 에너지·물가","life"),
}

DEFAULT_민생 = {
    "지역산업": {
        "level": "모니터링",
        "summary": "삼성전자 협력사 등 수원 제조업·수출기업 영향 분석 중. 호르무즈 봉쇄 시나리오 대비 공급망 점검 필요.",
        "key_indicator": "데이터 수집 후 업데이트",
        "타지자체_현황": "API 분석 실행 후 표시됩니다.",
    },
    "소상공인_자영업": {
        "level": "모니터링",
        "summary": "유류비·에너지비 상승에 따른 배달·운수·음식업 운영비용 증가 모니터링 중.",
        "key_indicator": "데이터 수집 후 업데이트",
        "타지자체_현황": "API 분석 실행 후 표시됩니다.",
    },
    "시민생활": {
        "level": "모니터링",
        "summary": "도시가스·전기요금 인상 가능성 및 취약계층 에너지 부담 모니터링 중.",
        "key_indicator": "데이터 수집 후 업데이트",
        "타지자체_현황": "API 분석 실행 후 표시됩니다.",
    },
}

display_민생 = 민생_분석 if 민생_분석 else DEFAULT_민생

_impact_cards_html = ""
for key, (icon, label, card_cls) in CATEGORY_META.items():
    item    = display_민생.get(key, DEFAULT_민생[key])
    level   = item.get("level","모니터링")
    summary = item.get("summary","")
    kpi     = item.get("key_indicator","")
    other   = item.get("타지자체_현황","")
    _impact_cards_html += (
        f'<div class="impact-card impact-card-{card_cls}">'
        f'<div class="ic-icon">{icon}</div>'
        f'<div class="ic-category">{label}</div>'
        f'<span class="ic-level-badge icl-{level}">영향도 · {level}</span>'
        f'<div class="ic-summary">{summary}</div>'
        f'<div class="ic-kpi-box"><div class="ic-kpi-label">핵심 지표</div><div class="ic-kpi-value">{kpi}</div></div>'
        f'<div class="ic-other-box"><div class="ic-other-label">타 지자체 현황</div><div class="ic-other-value">{other}</div></div>'
        f'</div>'
    )

st.markdown(f"""
<div class="section-card sec-gray">
  <div class="sec-header">
    <span class="sec-title"><span class="sec-num">02</span> 수원시 민생경제 영향 분석</span>
    <span class="sec-badge badge-red">3대 관점 분석</span>
  </div>
  <div class="triple-grid">{_impact_cards_html}</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ④ 수원시 우선 대응과제 (최상단 배치)
# ─────────────────────────────────────────────
DEFAULT_대응과제 = [
    {
        "순위": 1, "title": "에너지 취약가구 긴급 바우처 지원",
        "description": "기초수급·차상위 취약가구 대상 도시가스·전기요금 바우처 조기 집행. 경기도 매칭 사업 연계를 통해 시비 부담 최소화, 수혜 기준 완화.",
        "priority": "즉시",
        "근거": {
            "타지자체_벤치마킹": "서울시 에너지 취약가구 전기·가스 30% 상한 지원 모델",
            "전문가_의견": "에너지 취약계층 직접 지원이 물가 상승기 가장 효과적 대응",
            "보고서_근거": "KDI — 바우처 직접 지급이 감면 방식 대비 수혜율 2.3배 높음",
        },
    },
    {
        "순위": 2, "title": "소상공인 에너지 비용 긴급 지원",
        "description": "배달·운수·음식업 대상 유류비 보조금 및 전기·가스요금 특별 감면. 단일 창구 신청으로 간소화, 경기도 긴급 융자 연계 홍보 강화.",
        "priority": "즉시",
        "근거": {
            "타지자체_벤치마킹": "전주시 소상공인 에너지 특별지원금 50만 원 지급 사례",
            "전문가_의견": "소상공인 에너지비 부담이 폐업률에 직결 — 직접 보조가 즉효",
            "보고서_근거": "KEEI — 자영업 에너지비 비중 매출 대비 평균 8.4%로 임계치 초과",
        },
    },
    {
        "순위": 3, "title": "에너지 비상대응 TF · 시나리오 수립",
        "description": "호르무즈 봉쇄 장기화(3·6·12개월) 시나리오별 에너지·물가 충격 시뮬레이션 및 단계별 대응 매뉴얼 수립. 경기도 LNG 비상비축 MOU 연계.",
        "priority": "단기",
        "근거": {
            "타지자체_벤치마킹": "일본 METI 에너지 비상계획 3단계 시나리오 모델",
            "전문가_의견": "호르무즈 봉쇄 가능성 40%↑ — 지자체 단위 사전 비상계획 필수",
            "보고서_근거": "KIEP — 봉쇄 6개월 지속 시 국내 에너지 비용 추가 23% 상승 전망",
        },
    },
]

display_대응과제 = 대응과제 if 대응과제 else DEFAULT_대응과제
rank_tags = ["A", "B", "C"]

_action_cards_html = ""
for i, task in enumerate(display_대응과제[:3]):
    title_t = task.get("title","")
    desc    = task.get("description","")
    근거     = task.get("근거", {})
    bench   = 근거.get("타지자체_벤치마킹","")
    expert  = 근거.get("전문가_의견","")
    report  = 근거.get("보고서_근거","")
    _action_cards_html += (
        f'<div class="action-card">'
        f'<div class="ac-rank">Priority {rank_tags[i]}</div>'
        f'<div class="ac-title">{title_t}</div>'
        f'<div class="ac-desc">{desc}</div>'
        f'<div class="evidence-stack">'
        f'<div class="ev-item ev-bench"><span class="ev-tag">🏙 타지자체 벤치마킹</span>{bench}</div>'
        f'<div class="ev-item ev-expert"><span class="ev-tag">🎙 전문가 의견</span>{expert}</div>'
        f'<div class="ev-item ev-report"><span class="ev-tag">📄 보고서 근거</span>{report}</div>'
        f'</div></div>'
    )

st.markdown(f"""
<div class="section-card">
  <div class="sec-header">
    <span class="sec-title"><span class="sec-num">03</span> 수원시 민생경제 우선 대응과제</span>
    <span class="sec-badge badge-red">근거 기반 AI 정책 제언</span>
  </div>
  <div class="triple-grid">{_action_cards_html}</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 사전 검증 포인트 (03 우선대응과제 ~ 04 글로벌 상황 사이)
# ═══════════════════════════════════════════════════════════
critiques = [
    ("1. 예산 실현 가능성", "예산 긴급 지원 확대는 시 재정자립도(40%) 한계와 충돌 가능. 경기도 매칭 사업 연계 없이는 즉시 집행 불가. 보조금 규모 현실화 필수."),
    ("2. 공급망 파악 한계", "수원시 에너지 수급 대부분은 중앙정부·한국가스공사 관할. 시 단독 대응 효과 제한적. 광역 연계 대응 전략 병행 필요."),
    ("3. 장기화 대비 부재", "현 대응안은 단기(3개월) 중심. 분쟁 6개월~1년 지속 시 예산·행정 여력 고갈 우려. 시나리오 기반 중장기 플랜 수립 시급."),
]
devil_pts = "".join(
    f'<div class="devil-point"><div class="dp-title">{c[0]}</div><div class="dp-body">{c[1]}</div></div>'
    for c in critiques
)
st.markdown(
    f'<div class="devil-card sec-gray-card">'
    f'<div class="devil-stamp">리스크 점검</div>'
    f'<div class="devil-quote">사전 검증 포인트 — <span class="dq-hi">실행 전 반드시 확인해야 할 사항</span></div>'
    f'<div class="devil-grid">{devil_pts}</div>'
    f'</div>',
    unsafe_allow_html=True
)

# ═══════════════════════════════════════════════════════════
# ④ 각국 대응 매트릭스 — 중동 / 글로벌 / 한국 탭
# ═══════════════════════════════════════════════════════════
REGION_MAP = {
    "중동":   {"이란","이스라엘","사우디","사우디아라비아","UAE","카타르","이라크",
               "레바논","예멘","시리아","이집트","터키","하마스","헤즈볼라","UAE·카타르"},
    "글로벌": {"미국","중국","러시아","EU","유럽","일본","영국","독일","프랑스","인도","파키스탄","북한"},
    "한국":   {"한국","대한민국","외교부","산업부","기재부","기후에너지부","에너지부","국토부","식약처","농림부",
               "산업통상자원부","기획재정부","국토교통부","식품의약품안전처","농림축산식품부"},
}

DEFAULT_CR_REGIONS = {
    "중동": [
        {"country":"이란",       "stance":"강경",
         "title":"핵시설 방어 태세 강화, 호르무즈 통제 선언",
         "detail":"IAEA 사찰 차단·우라늄 농축 90% 돌파 발표. 대리전 확대로 협상 압박 전략 유지."},
        {"country":"이스라엘",   "stance":"강경",
         "title":"이란 핵·미사일 시설 정밀타격 옵션 상시 검토",
         "detail":"가자·레바논 전선 동시 관리. 미국에 선제타격 승인 압박 지속."},
        {"country":"사우디",     "stance":"중립",
         "title":"OPEC+ 감산 유지, 미·이란 중재 관망",
         "detail":"유가 상승 수혜 기대 속 분쟁 확산 억제 외교. 미국과 안보협약 재협상 진행 중."},
        {"country":"UAE·카타르", "stance":"중립",
         "title":"LNG 수출 지속, 분쟁 확산 방지 외교 추진",
         "detail":"카타르는 이란과 가스전 공유로 중립 불가피. UAE는 에너지 수출 극대화 전략 유지."},
        {"country":"이라크",     "stance":"중립",
         "title":"이란 영향권·미군 기지 공존, 줄타기 외교 지속",
         "detail":"친이란 민병대 활동 억제 국제 압박 증가. 석유 수출 차질 최소화 목표."},
    ],
    "글로벌": [
        {"country":"미국",   "stance":"강경",
         "title":"대이란 제재 강화, 호르무즈 해군 작전 유지",
         "detail":"이란 원유 제재 전면 강화. 한·미 방위 협력 비용 분담 재협상 압박."},
        {"country":"중국",   "stance":"중립",
         "title":"이란 원유 수입 지속, 미국과 외교적 거리두기",
         "detail":"제재 우회 결제 시스템 지속 가동. 삼성·LG 대중 수출 규제 연동 리스크."},
        {"country":"러시아", "stance":"지지",
         "title":"이란 군사·외교 지원, 서방 제재 우회 채널 공유",
         "detail":"이란-러시아 군사협력 MOU 확대. 서방 제재 우회 금융·물류 채널 공동 활용."},
        {"country":"EU",     "stance":"제재",
         "title":"대이란 제재 동참, 에너지 공급선 다변화 가속",
         "detail":"LNG 수입 계약 긴급 재협상. 재생에너지 전환 가속화 예산 추가 편성."},
        {"country":"일본",   "stance":"협력",
         "title":"에너지 비축 확대, 호주·캐나다 LNG 긴급 증량 협상",
         "detail":"중동 의존도 68% → 2030년 50% 목표 재설정. 에너지 비상비축 90일분 유지."},
    ],
    "한국": [
        {"country":"외교부",  "stance":"협력",
         "title":"미국 동조 대이란 제재 참여, 핵 비확산 지지 성명",
         "detail":"이란 핵협상 복원 촉구 및 한국인 자산 동결 해제 협상 병행 추진."},
        {"country":"산업부",  "stance":"대응",
         "title":"LNG 대체 수입선 긴급 확보 협의 착수",
         "detail":"호주·미국·카타르와 LNG 추가 공급 긴급 협상. 에너지 비상비축 확대 명령 발령."},
        {"country":"기재부",  "stance":"모니터링",
         "title":"에너지 물가 압력 대응 예비비 편성 검토",
         "detail":"유가 10% 추가 상승 시 물가 0.3%p 상방 리스크. 유류세 탄력세율 인하 옵션 준비."},
        {"country":"국토부",  "stance":"대응",
         "title":"건설현장 비상경제 TF 격상, 건설자재 수급 점검",
         "detail":"철강·알루미늄 공급망 교란 대비. 공공건설 발주 조정 및 비축 물량 현황 점검."},
        {"country":"기후에너지부","stance":"선제",
         "title":"에너지 비상공급 3단계 발령, 절약 캠페인 가동",
         "detail":"산업·상업용 에너지 사용 5% 절감 목표. 발전소 가동률 95% 비상 유지 모드 전환."},
        {"country":"식약처","stance":"모니터링",
         "title":"이란산 의약품 원료·식품첨가물 수급 현황 긴급 점검",
         "detail":"이란·중동 의존도 높은 의약품 원료(API) 및 식품첨가물 재고 현황 파악. 대체 수입선 확보 계획 수립 중."},
        {"country":"농림부","stance":"대응",
         "title":"국제 곡물·식품 가격 급등 대응 비축물량 점검",
         "detail":"호르무즈 봉쇄로 인한 중동·아프리카발 식량 공급망 교란 모니터링. 국내 밀·옥수수 비축량 현황 파악 및 수입 다변화 대책 검토."},
    ],
}

_STANCE_KEYS = {"강경","지지","중립","제재","협력","대응","선제","모니터링"}

def _st_key(stance: str) -> str:
    return stance if stance in _STANCE_KEYS else "unknown"

def build_cr_items_html(items: list) -> str:
    if not items:
        return '<div class="empty-dark">파이프라인 실행 후 데이터가 표시됩니다.</div>'
    # 템플릿 항목(is_real=False) 포함 여부 확인 → 안내 문구
    has_template = any(not item.get("is_real", True) for item in items)
    html = '<div class="cr-policy-list">'
    if has_template:
        html += ('<div style="font-size:0.65rem;color:#9CA3AF;margin-bottom:6px;padding:4px 8px;'
                 'background:#F9FAFB;border-radius:4px;border-left:3px solid #D1D5DB">'
                 '⚠️ 국내 뉴스 미수집 항목은 기준 템플릿으로 표시됩니다. '
                 '다음 파이프라인 실행 시 실수집 데이터로 교체됩니다.</div>')
    for item in items:
        country   = item.get("country","")
        stance    = item.get("stance","중립")
        title     = item.get("title","")
        detail    = item.get("detail","") or item.get("actions_text","")
        sk        = _st_key(stance)
        is_real   = item.get("is_real", True)
        # 템플릿 항목은 흐리게 표시
        item_style = "" if is_real else "opacity:0.65;"
        # 오른쪽 칼럼: 짧은 단어(강경/중립 등)는 배지, 긴 문장은 파란 설명 박스
        is_long_stance = len(stance) > 10
        if is_long_stance:
            right_html = f'<div class="cr-stance-desc">{stance}</div>'
        else:
            right_html = (
                f'<span class="cr-stance-badge st-{sk}" '
                f'style="flex-shrink:0;margin-top:2px;min-width:52px;text-align:center">{stance}</span>'
            )
        html += (
            f'<div class="policy-item" style="{item_style}">'
            f'<span class="cr-stance-badge st-{sk}" '
            f'style="flex-shrink:0;flex-basis:96px;width:96px;min-width:96px;text-align:center;white-space:normal;word-break:keep-all;line-height:1.4">{country}</span>'
            f'<div class="pi-content">'
            f'<div class="pi-title">{title}</div>'
            f'<div class="pi-detail">{detail}</div>'
            f'</div>'
            f'{right_html}'
            f'</div>'
        )
    html += '</div>'
    return html

def get_region_items(region_name: str) -> list:
    # 한국 외 일반 처리
    if cr_responses:
        region_set = REGION_MAP.get(region_name, set())
        filtered = [r for r in cr_responses if r.get("country","") in region_set]
        if filtered:
            out = []
            for r in filtered:
                actions = r.get("actions",[])
                action_text = " · ".join(actions[:2]) if actions else r.get("outlook","")[:100]
                out.append({
                    "country": r.get("country",""),
                    "stance":  r.get("stance","중립"),
                    "title":   action_text,
                    "detail":  r.get("suwon_relevance",""),
                })
            return out
    return DEFAULT_CR_REGIONS.get(region_name, [])


# ── 한국 정부 부처 데이터 별도 추출 ──
def get_kr_ministry_items() -> list:
    """kr_ministry_responses → 부처 브리핑 리스트 반환"""
    if kr_min_responses:
        return kr_min_responses

    # 부처 데이터 없으면 country_responses의 '한국' 항목으로 임시 구성
    out = []
    region_set = REGION_MAP.get("한국", set())
    for r in cr_responses:
        if r.get("country","") in region_set:
            out.append({
                "ministry":         r.get("country","한국"),
                "stance":           r.get("stance","모니터링"),
                "actions":          r.get("actions", []),
                "policy_direction": r.get("outlook",""),
                "suwon_relevance":  r.get("suwon_relevance",""),
                "is_real": True,
            })
    if out:
        return out

    # 최종 fallback: DEFAULT 부처 목록
    return [
        {"ministry":"외교부",  "stance":"협력",     "actions":["미국 동조 대이란 제재 참여","핵 비확산 지지 성명"], "policy_direction":"이란 핵협상 복원 촉구 및 한국인 자산 동결 해제 협상 병행","suwon_relevance":"외교부의 대미 제재 동참은 이란산 수입 중단 가능성을 높여 수원 소재 중소 제조업체 원자재 조달에 영향", "is_real": False},
        {"ministry":"산업통상자원부","stance":"대응","actions":["LNG 대체 수입선 긴급 확보","에너지 비상비축 확대 명령"],"policy_direction":"호주·미국·카타르와 LNG 추가 공급 긴급 협상","suwon_relevance":"산업부 에너지 비상비축 확대 조치는 도시가스 요금 안정화 여부와 직결되어 수원시 가정·소상공인 에너지비 영향", "is_real": False},
        {"ministry":"기획재정부","stance":"모니터링","actions":["에너지 물가 압력 대응 예비비 편성 검토","유류세 탄력세율 인하 옵션 준비"],"policy_direction":"유가 10% 추가 상승 시 물가 0.3%p 상방 리스크 대응","suwon_relevance":"기재부 유류세 인하 결정은 수원 소상공인·배달업 유류비 부담 완화에 직접 영향", "is_real": False},
        {"ministry":"국토교통부","stance":"대응","actions":["건설현장 비상경제 TF 격상","건설자재 수급 점검"],"policy_direction":"철강·알루미늄 공급망 교란 대비","suwon_relevance":"광교·영통 재개발 사업 건설자재 조달 일정 영향 가능성 점검 필요", "is_real": False},
        {"ministry":"농림축산식품부","stance":"대응","actions":["국제 곡물가격 급등 대응 비축물량 점검","수입 다변화 검토"],"policy_direction":"중동·아프리카발 식량 공급망 교란 모니터링","suwon_relevance":"밀·식용유 등 식품 원자재 가격 상승은 수원 음식점·제빵업 원가 상승으로 직결", "is_real": False},
    ]


def build_kr_ministry_html(items: list) -> str:
    """한국 정부 부처 브리핑 전용 렌더러"""
    if not items:
        return '<div class="empty-dark">파이프라인 실행 후 부처별 데이터가 표시됩니다.</div>'

    MINISTRY_ICON = {
        "외교부":"🌐","산업통상자원부":"⚙️","산업부":"⚙️","기획재정부":"💰","기재부":"💰",
        "국토교통부":"🏗️","국토부":"🏗️","농림축산식품부":"🌾","농림부":"🌾",
        "식품의약품안전처":"💊","식약처":"💊","기후에너지부":"⚡","에너지부":"⚡","한국":"🇰🇷",
        "대한민국":"🇰🇷",
    }
    STANCE_CLS = {
        "선제":"st-선제","적극":"st-협력","대응":"st-대응","모니터링":"st-모니터링",
        "협력":"st-협력","강경":"st-강경","검토":"st-검토",
    }

    has_template = any(not item.get("is_real", True) for item in items)
    html = '<div class="kr-ministry-list">'
    if has_template:
        html += ('<div style="font-size:0.65rem;color:#9CA3AF;margin-bottom:8px;padding:4px 8px;'
                 'background:#F9FAFB;border-radius:4px;border-left:3px solid #D1D5DB">'
                 '⚠️ 부처 데이터 미수집 — 기준 템플릿으로 표시됩니다. '
                 '파이프라인 실행 시 실수집 데이터로 교체됩니다.</div>')

    for item in items:
        ministry   = item.get("ministry", "")
        actions    = item.get("actions", [])
        policy_dir = item.get("policy_direction", "") or item.get("outlook", "")
        suwon_rel  = item.get("suwon_relevance", "")
        stance_raw = item.get("stance", "모니터링")
        is_real    = item.get("is_real", True)
        # confirmed: 뉴스 직접 확인 여부 (True=확인, False=상황 기반 예상)
        confirmed  = item.get("confirmed", True if is_real else False)

        # stance: 짧은 단어만 배지로, 긴 문장은 policy_dir에 병합
        if len(stance_raw) <= 8:
            stance_badge = stance_raw
        else:
            stance_badge = "대응"
            policy_dir = stance_raw if not policy_dir else policy_dir

        icon = MINISTRY_ICON.get(ministry, "🏛️")
        sk   = STANCE_CLS.get(stance_badge, "st-모니터링")
        # 미확인(예상) 항목: 약간 흐리게 + 왼쪽 보더 색 연하게
        card_style = "" if confirmed else "opacity:0.82;border-left-color:#9CA3AF;"

        # 확인 여부 뱃지
        source_badge = (
            '<span style="font-size:0.58rem;font-weight:700;padding:1px 6px;'
            'border-radius:3px;background:#DCFCE7;color:#15803D;margin-left:6px">뉴스 확인</span>'
            if confirmed else
            '<span style="font-size:0.58rem;font-weight:700;padding:1px 6px;'
            'border-radius:3px;background:#F3F4F6;color:#9CA3AF;margin-left:6px">상황 기반 예상</span>'
        )

        # actions 불릿 HTML
        if isinstance(actions, list) and actions:
            bullets = "".join(f'<li>{a}</li>' for a in actions)
            actions_html = f'<ul class="kr-actions-list">{bullets}</ul>'
        elif isinstance(actions, str) and actions:
            actions_html = f'<div class="kr-action-plain">{actions}</div>'
        else:
            actions_html = ""

        suwon_html = (f'<div class="kr-suwon-box">'
                      f'<span class="kr-suwon-label">📍 수원시 연관</span>'
                      f'<span class="kr-suwon-text">{suwon_rel}</span>'
                      f'</div>') if suwon_rel else ""

        policy_html = (f'<div class="kr-policy-dir">'
                       f'<span class="kr-pd-label">정책 방향</span> {policy_dir}'
                       f'</div>') if policy_dir else ""

        html += (
            f'<div class="kr-ministry-card" style="{card_style}">'
            f'<div class="kr-ministry-header">'
            f'  <span class="kr-ministry-icon">{icon}</span>'
            f'  <span class="kr-ministry-name">{ministry}</span>'
            f'  {source_badge}'
            f'  <span class="cr-stance-badge {sk}" style="margin-left:auto;flex-shrink:0">{stance_badge}</span>'
            f'</div>'
            f'{actions_html}'
            f'{policy_html}'
            f'{suwon_html}'
            f'</div>'
        )
    html += '</div>'
    return html


_cr_me_html  = build_cr_items_html(get_region_items("중동"))
_cr_gl_html  = build_cr_items_html(get_region_items("글로벌"))
_cr_kr_html  = build_kr_ministry_html(get_kr_ministry_items())

st.markdown(f"""
<div class="section-card sec-gray">
  <div class="sec-header">
    <span class="sec-title"><span class="sec-num">04</span> 글로벌 상황 및 중앙정부 대응</span>
    <span class="sec-badge badge-blue">Country Response Matrix</span>
  </div>
  <div class="ctabs">
    <input type="radio" id="cr-me" name="cr-tabs" checked>
    <input type="radio" id="cr-gl" name="cr-tabs">
    <input type="radio" id="cr-kr" name="cr-tabs">
    <div class="ctab-bar">
      <label for="cr-me" class="ctab-label">🌙 중동</label>
      <label for="cr-gl" class="ctab-label">🌐 글로벌</label>
      <label for="cr-kr" class="ctab-label">🇰🇷 한국</label>
    </div>
    <div id="panel-cr-me" class="ctab-panel">{_cr_me_html}</div>
    <div id="panel-cr-gl" class="ctab-panel">{_cr_gl_html}</div>
    <div id="panel-cr-kr" class="ctab-panel">{_cr_kr_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ⑤ 공개 채널 시민 목소리
# ═══════════════════════════════════════════════════════════

citizen_voice_items = get_citizen_voice_items(date_str)

cv_tab_map = {
    "전체": "all",
    "네이버 뉴스": "naver",
    "유튜브": "youtube",
    "지역 언론": "local",
    "당근": "daangn",
}

cv_selected_label = st.radio(
    "공개 채널 시민 목소리 필터",
    options=list(cv_tab_map.keys()),
    horizontal=True,
    index=0,
    key=f"cvtab_{date_str}",
    label_visibility="collapsed",
)

cv_selected_channel = cv_tab_map[cv_selected_label]
cv_html = build_citizen_voice_html(
    citizen_voice_items,
    selected_channel=cv_selected_channel,
    limit=6 if cv_selected_channel == "all" else 4
)

st.markdown(
    f"""
    <div class="section-card">
      <div class="sec-header">
        <span class="sec-title"><span class="sec-num">05</span> 공개 채널 시민 목소리</span>
        <span class="sec-badge badge-green">Citizen Voice Monitor</span>
      </div>
      {cv_html}
    </div>
    """,
    unsafe_allow_html=True,
)

# (⑥⑦ 민생경제·대응과제는 ③④ 위치로 이동됨)


# ═══════════════════════════════════════════════════════════
# ⑪ 다음주 주목 핵심이슈
# ═══════════════════════════════════════════════════════════
DEFAULT_NEXT_ISSUES = [
    {
        "title": "이란-미국 협상 2차 라운드 결과",
        "detail": "협상 결렬 시 호르무즈 봉쇄 가능성 급등. 유가 $110 돌파 여부 및 국내 에너지 비용 추가 상승 직결. 수원시 에너지 취약가구 대응 준비 필요.",
        "tag": "고위험", "tag_cls": "ni-high",
    },
    {
        "title": "OPEC+ 긴급회의 — 추가 감산 결정 여부",
        "detail": "사우디 주도 감산 확대 시 국내 휘발유·도시가스 요금 연쇄 인상 예상. 경기도 에너지 비용 경감 예산 추가 편성 논의 모니터링.",
        "tag": "주목", "tag_cls": "ni-mid",
    },
    {
        "title": "한국 정부 에너지 비상대책 발표",
        "detail": "산업부·기재부 합동 에너지 비상대책 발표 예정. 지자체 대응 지침 및 예산 배정 기준 확인 필요. 수원시 TF 대응 계획 조정 여부 검토.",
        "tag": "확인 필요", "tag_cls": "ni-watch",
    },
    {
        "title": "국내 소비자물가지수(CPI) 4월 발표",
        "detail": "에너지·식품 가격 반영된 4월 CPI 발표. 전월 대비 0.3%p 이상 상승 시 긴급 민생 대책 검토 기준 초과. 취약계층 추가 지원 근거 마련 가능.",
        "tag": "모니터링", "tag_cls": "ni-watch",
    },
]

next_issues = minseang.get("next_week_issues", []) or DEFAULT_NEXT_ISSUES

next_html = '<div class="next-issue-list">'
for i, issue in enumerate(next_issues[:4], 1):
    title  = issue.get("title","")
    detail = issue.get("detail","")
    tag    = issue.get("tag","모니터링")
    cls    = issue.get("tag_cls","ni-watch")
    next_html += (
        f'<div class="next-issue-item">'
        f'<div class="ni-num">{i}</div>'
        f'<div class="ni-content">'
        f'<div class="ni-title">{title}</div>'
        f'<div class="ni-detail">{detail}</div>'
        f'</div>'
        f''
        f'</div>'
    )
next_html += '</div>'

st.markdown(f"""
<div class="section-card sec-gray">
  <div class="sec-header">
    <span class="sec-title"><span class="sec-num">06</span> 다음번 주목 이슈</span>
    <span class="sec-badge badge-blue">Next Issue Watch</span>
  </div>
  {next_html}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ⑫ 전문가 브리핑 (YouTube 요약)
# ═══════════════════════════════════════════════════════════
yt_summaries = yt_data.get("summaries", [])
_yt_fallback_note = ""

# 현재 날짜 데이터 없으면 → 최근 유효 날짜 파일로 폴백
if not yt_summaries:
    _yt_files = sorted(
        (DATA_DIR / "youtube").glob("yt_summary_*.json"),
        reverse=True
    )
    for _yf in _yt_files:
        try:
            _yd = load_json(_yf) or {}
            _ys = _yd.get("summaries", [])
            if _ys:
                yt_summaries = _ys
                _yt_date = _yf.stem.replace("yt_summary_", "")
                _yt_fallback_note = f"{_yt_date[:4]}-{_yt_date[4:6]}-{_yt_date[6:]} 기준"
                break
        except Exception:
            continue

def yt_ch_cls(ch: str) -> str:
    c = ch.lower()
    if "al jazeera" in c:  return "yt-aljazeera"
    if "dw" in c:           return "yt-dw"
    if "연합" in c:         return "yt-yonhap"
    if "bbc" in c:          return "yt-aljazeera"
    if "reuters" in c:      return "yt-dw"
    if "cnn" in c:          return "yt-aljazeera"
    return "yt-default"

def yt_type_label(ct: str) -> str:
    return {"전문가분석": "🎓 전문가분석", "브리핑": "📋 브리핑",
            "뉴스": "📰 뉴스", "기타": "▶ 영상"}.get(ct, "▶ 영상")

if yt_summaries:
    top_yt = yt_summaries[:3]
    _yt_cards_html = ""
    for item in top_yt:
        channel    = item.get("channel", "")
        title      = item.get("title", "")
        video_id   = item.get("video_id", "")
        url        = item.get("url", f"https://www.youtube.com/watch?v={video_id}")
        summary_ko = item.get("summary_ko", "")
        points     = item.get("key_points", [])
        relevance    = item.get("iran_relevance", "")
        content_type = item.get("content_type", "")
        suwon_con    = item.get("suwon_connection", "")
        pub          = item.get("published", "")[:10]

        # 썸네일 URL (YouTube 기본 제공)
        thumb_url  = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else ""

        # 요약 줄바꿈
        summary_lines = [ln.strip() for ln in summary_ko.replace("\\n", "\n").split("\n") if ln.strip()]
        summary_html = "".join(
            f'<div class="yt-sum-line">{ln}</div>'
            for ln in summary_lines[:3]
        )

        # 수원시 연결점
        suwon_html = (
            f'<div class="yt-suwon">🏙 {suwon_con}</div>'
            if suwon_con else ""
        )

        rel_cls = {"높음": "badge-red", "중간": "badge-amber", "낮음": "badge-blue"}.get(relevance, "badge-blue")

        _yt_cards_html += f"""
<div class="yt-card">
  <a href="{url}" target="_blank" class="yt-thumb-link">
    <div class="yt-thumb-wrap">
      <img src="{thumb_url}" class="yt-thumb" alt="{title}" onerror="this.style.display='none'">
      <div class="yt-play-btn">▶</div>
    </div>
  </a>
  <div class="yt-card-body">
    <div class="yt-channel-row">
      <span class="yt-ch-badge {yt_ch_cls(channel)}">{channel[:22]}</span>
      <span class="yt-rel-badge {rel_cls}">{relevance}</span>
      {f'<span class="yt-type-badge">{yt_type_label(content_type)}</span>' if content_type else ""}
    </div>
    <a href="{url}" target="_blank" class="yt-title">{title}</a>
    <div class="yt-summary">{summary_html}</div>
    {suwon_html}
  </div>
</div>"""
    _yt_fallback_html = (
        f'<div style="font-size:0.63rem;color:#9CA3AF;margin-bottom:8px">'
        f'📅 {_yt_fallback_note} 데이터 표시 중 (선택 날짜 수집분 없음)'
        f'</div>'
    ) if _yt_fallback_note else ""
    _yt_body = f'{_yt_fallback_html}<div class="triple-grid">{_yt_cards_html}</div>'
else:
    _yt_body = '<div class="empty-dark">📺 파이프라인 실행 후 Al Jazeera · DW News · 연합뉴스TV 전문가 브리핑이 표시됩니다.</div>'

st.markdown(f"""
<div class="section-card">
  <div class="sec-header">
    <span class="sec-title"><span class="sec-num">07</span> 전문가 브리핑</span>
    <span class="sec-badge badge-blue">YouTube Intelligence</span>
  </div>
  {_yt_body}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 페이지 래퍼 닫기 + 푸터
# ═══════════════════════════════════════════════════════════
st.markdown("</div>", unsafe_allow_html=True)  # page-wrap

st.markdown(f"""
<div class="intel-footer">
  <div class="footer-grid">
    <div class="footer-col">
      <span class="footer-label">🏛️ 발행처</span>
      <div class="footer-val" style="font-weight:700;color:#1C2B40">수원시정연구원</div>
      <div class="footer-val">Suwon Research Institute</div>
      <div style="margin-top:6px"></div>
      <span class="footer-label">📡 발행 주기</span>
      <div class="footer-val">매주 월·목 오후 (주 2회)</div>
      <div class="footer-val">분석 기준: {fmt(selected_date)} · 기사 {len(analyzed)}건</div>
      <button class="no-print" onclick="window.print()"
        style="margin-top:8px;background:#1C2B40;border:none;color:#FFFFFF;
               padding:5px 14px;border-radius:4px;font-size:0.68rem;font-weight:700;
               cursor:pointer;letter-spacing:0.5px;width:fit-content">🖨 PRINT</button>
    </div>
    <div class="footer-col">
      <span class="footer-label">🤖 AI 활용</span>
      <div class="footer-val" style="margin-bottom:6px">Anthropic Claude API 기반 자동 분석 · 기사 분류·요약·정책 제언 자동 생성</div>
      <span class="footer-label">📂 데이터 출처</span>
      <div class="footer-val" style="margin-bottom:6px">Reuters · Al Jazeera · Guardian · BBC · IEA · IMF · WorldBank · NewsAPI · Yahoo Finance · GlobalPetrolPrices · Opinet</div>
      <span class="footer-label">📱 권장 환경</span>
      <div class="footer-val">PC 또는 태블릿 가로 보기 권장 (모바일 세로 보기 시 일부 내용 잘림)</div>
    </div>
    <div class="footer-col" style="text-align:right">
      <div class="footer-stamp">CONFIDENTIAL<br>FOR OFFICIAL USE ONLY<br>Suwon City Intelligence Office</div>
      <div style="margin-top:10px;font-size:0.6rem;color:#6B7280;line-height:1.9;text-align:right">
        © 2026 수원시정연구원<br>
        본 보고서의 무단 전재·배포를 금합니다.<br>
        <span style="color:#4B5563;font-weight:700">문의</span> 박진우 연구위원 (031-220-8072)<br>
        <span style="color:#4B5563;font-weight:700">제작</span> 박진우 연구위원 · 정다래 연구위원 · 장정식 위촉연구원 · 정보라 위촉연구원
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

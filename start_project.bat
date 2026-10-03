@echo off
chcp 65001 > nul
title Tadbir Chiptalari Serveri
color 0B
echo ======================================================================
echo           TADBIR CHIPTALARI - LOYIHASINI ISHGA TUSHIRISH
echo ======================================================================
echo.
echo Server ishga tushmoqda, iltimos kuting...
echo.

:: Brauzerda saytni avtomatik ochish (2 soniyadan so'ng)
start "" "http://127.0.0.1:8000"

:: Python orqali serverni yurgizish
python run.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Xatolik: Python topilmadi yoki server to'xtadi.
    pause
)

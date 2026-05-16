# Projet pour pyside6-lupdate
# Lance : pyside6-lupdate riskpulse.pro
# Genere : riskpulse_<lang>.ts a partir de tous les tr() dans le code Python.

SOURCES = ../i18n.py \
          ../main_window.py \
          ../theme.py \
          ../components/sidebar.py \
          ../components/topbar.py \
          ../components/statusbar.py \
          ../components/card.py \
          ../components/toast.py \
          ../components/command_palette.py \
          ../components/about_dialog.py \
          ../components/splash.py \
          ../components/login_dialog.py \
          ../components/user_badge.py \
          ../views/_base.py \
          ../views/welcome_view.py \
          ../views/analyse_view.py \
          ../views/intelligence_view.py \
          ../views/knowledge_view.py \
          ../views/monitoring_view.py \
          ../views/banking_view.py \
          ../views/predictive_view.py \
          ../views/insights_view.py \
          ../views/api_view.py \
          ../views/users_view.py \
          ../views/propagation_view.py \
          ../views/comparaison_view.py \
          ../views/contrefactuel_view.py \
          ../views/traduction_view.py \
          ../views/dashboard_view.py \
          ../views/parametres_view.py

TRANSLATIONS = riskpulse_fr.ts \
               riskpulse_en.ts \
               riskpulse_ar.ts \
               riskpulse_it.ts \
               riskpulse_es.ts

CODECFORSRC = UTF-8

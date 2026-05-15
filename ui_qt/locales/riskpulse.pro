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
          ../views/_base.py \
          ../views/analyse_view.py \
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

# cryptobot

Ici, le détail des étapes
Debian 12.9 sur virtualbox
Debian plutôt que Alpine pour la compatibilité des modules python

VM : new:new root:

Un grand Merci à Chat-GPT

API key : 67be022945e41a0001668f7e
passphrase : fromrsatothemoon - ca6f8519-8b50-4236-ab2f-108a23203f5b | Pas de restriction toutes les autorisations

Langage : python
 - CCXT le mégabundle yatouskifo
 - Yahoo finance (yfinance) pour récupérer les valeurs des marchés

sudo apt update && apt upgrade
python 3.11.2
pip 23.0.1

[Installation des modules ccxt puis yfinance

pip install ccxt --break-system-packages !!!!
pip install yfinance --break-system-packages]

Selon Chat-GPT

3️⃣ Créer un environnement virtuel (optionnel mais recommandé)

python3 -m venv trading-bot
source trading-bot/bin/activate

de là : pip install ccxt yfinance pandas numpy ta requests
Plus de message d'erreur !







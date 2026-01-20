# Samsung Smart TV Enhanced - OAuth2 Integration

## Overview

Cette mise à jour ajoute le support **OAuth2 autonome** pour l'intégration Samsung Smart TV Enhanced.  
L'intégration peut maintenant fonctionner de 3 façons :

| Méthode | Description |
|---------|-------------|
| **OAuth2** ⭐ | Authentification via Samsung Developer Portal - Token auto-refresh |
| **PAT** | Personal Access Token (legacy) |
| **ST Integration** | Réutilise le token de l'intégration SmartThings native |

## Fichiers modifiés

```
samsungtv_artmode/
├── manifest.json          # ✅ Ajout dépendance "application_credentials"
├── const.py               # ✅ Nouvelles constantes OAuth
├── config_flow.py         # ✅ Support OAuth2 complet
├── oauth_helper.py        # ✅ NOUVEAU - Gestion des tokens OAuth
├── strings.json           # ✅ Messages OAuth
└── application_credentials.py  # (déjà présent)
```

## Installation

### 1. Remplacer les fichiers

Copie ces fichiers dans `custom_components/samsungtv_artmode/` :
- `manifest.json`
- `const.py`
- `config_flow.py`
- `oauth_helper.py`
- `strings.json`

### 2. Redémarre Home Assistant

### 3. Créer une App SmartThings (une seule fois)

1. Va sur https://developer.smartthings.com/
2. Connecte-toi avec ton compte Samsung
3. **New Project** → "Automation for the Home"
4. Donne un nom (ex: "Home Assistant TV")
5. Dans le sidebar: **Register App** → "OAuth2 / Credentials"
6. Remplis:
   - **App Name**: Home Assistant Samsung TV
   - **Redirect URI**: `https://my.home-assistant.io/redirect/oauth`
   - **Scopes**: ✅ `r:devices:*` et ✅ `x:devices:*`
7. **Save** → copie **Client ID** et **Client Secret**

### 4. Ajouter les credentials dans Home Assistant

1. **Paramètres** → **Appareils & Services**
2. Menu ⋮ → **Application Credentials**
3. **+ Add Application Credentials**
4. Sélectionne "Samsung Smart TV Enhanced"
5. Colle ton Client ID et Client Secret
6. **Add**

### 5. Configurer l'intégration

1. **Paramètres** → **Appareils & Services** → **+ Add Integration**
2. Cherche "Samsung Smart TV Enhanced"
3. Sélectionne **🔐 OAuth2 (Recommended)**
4. Tu seras redirigé vers la page de login Samsung
5. Autorise les permissions
6. Sélectionne ta TV et entre son IP

## Fonctionnement OAuth

```
┌───────────────────────────────────────────────────────┐
│                    OAuth2 Token Lifecycle              │
├───────────────────────────────────────────────────────┤
│                                                        │
│  Authentification initiale:                           │
│  User login → Access Token (24h) + Refresh Token      │
│                                                        │
│  Opération normale:                                    │
│  Token valide → Utiliser access_token pour API        │
│                                                        │
│  Token expiré:                                         │
│  Token expire → Auto-refresh via refresh_token        │
│               → Nouveau access_token sauvegardé       │
│                                                        │
│  Refresh échoue:                                       │
│  Refresh fail → Déclenche flux de ré-authentification │
│                                                        │
└───────────────────────────────────────────────────────┘
```

## Migration depuis PAT

Si tu as déjà configuré l'intégration avec un PAT :

1. Va dans les **options** de l'intégration
2. Clique sur **Reconfigurer**
3. Coche **🔄 Switch to OAuth2 authentication**
4. Suis le flux OAuth

## Troubleshooting

### "OAuth not configured"
→ Ajoute d'abord les Application Credentials (étape 4)

### "No Samsung TVs found"
→ Vérifie que ta TV est enregistrée dans l'app SmartThings
→ Vérifie que tu as accordé les bons scopes (r:devices:*, x:devices:*)

### "Token refresh failed"
→ Vérifie la connexion internet
→ Re-authentifie via le flux reauth
→ Vérifie que ton app OAuth est toujours active sur developer.smartthings.com

## Notes techniques

- Les tokens OAuth SmartThings expirent après **24 heures**
- Le refresh automatique se fait **5 minutes** avant l'expiration
- Les tokens sont stockés de manière sécurisée dans la config entry
- Backward compatible avec PAT et ST Integration existants

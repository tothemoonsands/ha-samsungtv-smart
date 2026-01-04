# Samsung TV ArtMode - v6.3.0 (OAuth2 Support)

## 🎯 Nouveauté : Authentification OAuth2 SmartThings

Cette version ajoute le support OAuth2 pour l'authentification SmartThings, permettant de se connecter directement avec son compte Samsung sans avoir à créer un Personal Access Token manuellement.

## 📋 Méthodes d'authentification

### Option 1 : OAuth2 (Sign in with Samsung) ⭐ NOUVEAU

**Prérequis :**
1. Créer une application OAuth sur le [SmartThings Developer Portal](https://developer.smartthings.com/)
2. Configurer les Application Credentials dans Home Assistant

**Étapes de configuration :**

1. **Créer l'application SmartThings :**
   - Aller sur https://developer.smartthings.com/
   - Se connecter avec votre compte Samsung
   - Créer un nouveau projet
   - Ajouter un client OAuth
   - Redirect URI : `https://my.home-assistant.io/redirect/oauth`
   - Noter le **Client ID** et **Client Secret**

2. **Configurer Home Assistant :**
   - Aller dans **Paramètres → Appareils & Services**
   - Cliquer sur les ⋮ (3 points) → **Identifiants d'application**
   - Cliquer sur **+ Ajouter des identifiants**
   - Sélectionner **SamsungTV ArtMode**
   - Entrer le Client ID et Client Secret

3. **Ajouter l'intégration :**
   - Ajouter l'intégration Samsung TV ArtMode
   - Choisir **"Sign in with Samsung (OAuth2)"**
   - Suivre le flux de connexion Samsung
   - Configurer l'IP de votre TV
   - **C'est fait !** ✨

### Option 2 : Personal Access Token (Manuel)

Pour ceux qui préfèrent la méthode manuelle :

1. Créer un token sur https://account.smartthings.com/tokens
2. Ajouter l'intégration Samsung TV ArtMode
3. Choisir **"Personal Access Token"**
4. Coller votre token
5. Configurer l'IP de votre TV

### Option 3 : SmartThings Integration Link

Si vous avez déjà l'intégration SmartThings native configurée :

1. Ajouter l'intégration Samsung TV ArtMode
2. Choisir **"Personal Access Token"**
3. Sélectionner votre intégration SmartThings dans le dropdown
4. Configurer l'IP de votre TV

## 🔄 Migration PAT → OAuth

Si vous utilisez actuellement un PAT et souhaitez passer à OAuth :

1. Configurer les Application Credentials (voir ci-dessus)
2. Aller dans **Paramètres → Appareils & Services → Samsung TV ArtMode**
3. Cliquer sur les ⋮ → **Reconfigurer**
4. Cocher **"Switch to OAuth2 authentication"**
5. Suivre le flux OAuth

## 📦 Fichiers modifiés

| Fichier | Description |
|---------|-------------|
| `application_credentials.py` | **NOUVEAU** - Configuration OAuth2 |
| `config_flow.py` | Flux avec choix OAuth/PAT |
| `__init__.py` | Support OAuth2Session + token refresh |
| `const.py` | Constantes OAuth (scopes, AuthMode) |
| `manifest.json` | Dépendance application_credentials |
| `strings.json` | Textes UI pour OAuth |

## ⚙️ Comment fonctionne OAuth2

1. **Authentification** : L'utilisateur se connecte via Samsung Account
2. **Token** : SmartThings retourne un access_token + refresh_token
3. **Stockage** : Le token est stocké dans `entry.data["oauth_token"]`
4. **Refresh** : `OAuth2Session.async_ensure_token_valid()` rafraîchit automatiquement
5. **Utilisation** : `async_get_smartthings_token()` retourne toujours un token valide

## ⚠️ Notes importantes

### Redirect URI

Le redirect URI doit être exactement :
```
https://my.home-assistant.io/redirect/oauth
```

### Scopes requis

L'intégration demande les scopes suivants :
- `r:devices:*` - Lecture des appareils
- `w:devices:*` - Écriture sur les appareils  
- `x:devices:*` - Exécution de commandes
- `r:locations:*` - Lecture des emplacements

### Compatibilité

- ✅ 100% rétrocompatible avec les configs PAT existantes
- ✅ Toutes les fonctionnalités existantes conservées
- ✅ Frame Art Mode
- ✅ Power Switch SmartThings
- ✅ Light sensors

---

**Version:** 6.3.0  
**Date:** 2024-12-10


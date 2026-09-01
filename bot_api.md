# API FrenchBreaches — Intégration bot Discord

API publique et gratuite pour interroger les fuites de données recensées par **FrenchBreaches**. Conçue pour les bots Discord (embeds). Read-only, sans clé API.

- **Base URL :** `https://frenchbreaches.com/api/bot.php`
- **Format :** JSON UTF-8 (`Content-Type: application/json`)
- **Méthodes :** `GET` uniquement (CORS ouvert)
- **Cache HTTP :** 60–300 s selon l'endpoint
- **Limite :** 300 requêtes / heure / IP (`429 Too Many Requests` au-delà)

---

## 1. Endpoints

### 1.1 Rechercher une fuite — `/fuite`

| Paramètre | Type   | Requis | Description                                                                |
| ---------- | ------ | ------ | -------------------------------------------------------------------------- |
| `action` | string | ✅     | `fuite`                                                                  |
| `q`      | string | ✅     | Nom d'entreprise ou mot-clé (2 à 80 caractères)                         |
| `sector` | string | ❌     | Filtre par secteur (insensible à la casse et aux accents, ex.`telecom`) |

Retourne **5 résultats max**, classés par pertinence puis date.

```
GET /api/bot.php?action=fuite&q=free
GET /api/bot.php?action=fuite&q=free&sector=telecom
```

### 1.2 Détail d'une fuite — `/detail`

| Paramètre | Type   | Requis | Description                                                             |
| ---------- | ------ | ------ | ----------------------------------------------------------------------- |
| `action` | string | ✅     | `detail`                                                              |
| `id`     | string | ✅     | Identifiant de la fuite (champ`id` renvoyé par les autres endpoints) |

Renvoie une seule fuite **complète** : description non tronquée + images (URLs absolues). Parfait pour un embed riche sur `/alerte`.

```
GET /api/bot.php?action=detail&id=mt4685xhf4it99ffgkq
```

### 1.3 Dernières fuites — `/dernieres`

| Paramètre | Type          | Requis | Description                                                                          |
| ---------- | ------------- | ------ | ------------------------------------------------------------------------------------ |
| `action` | string        | ✅     | `dernieres`                                                                        |
| `limit`  | int           | ❌     | Nombre de résultats (1 à 25, défaut`10`)                                        |
| `since`  | date ISO 8601 | ❌     | Ne renvoie que les fuites publiées**après** cette date (base du mode alerte) |
| `sector` | string        | ❌     | Filtre par secteur (ex.`commerce`, `secteur public`)                             |

Sans `since`, renvoie les `limit` dernières fuites. Avec `since`, renvoie toutes les fuites plus récentes que la date donnée.

```
GET /api/bot.php?action=dernieres&limit=5
GET /api/bot.php?action=dernieres&since=2026-08-22T09:00:00Z
GET /api/bot.php?action=dernieres&sector=telecom&limit=3
```

### 1.4 Statistiques globales — `/stats`

| Paramètre | Type   | Requis | Description |
| ---------- | ------ | ------ | ----------- |
| `action` | string | ✅     | `stats`   |

```
GET /api/bot.php?action=stats
```

---

## 2. Format de réponse

Structure commune :

```json
{
  "success": true,
  "endpoint": "fuite",
  "count": 5,
  "data": [ { "fuite": {…} } ],
  "generated_at": "2026-08-28T22:14:17+00:00"
}
```

### Objet fuite

| Champ              | Type         | Description                                                                                |
| ------------------ | ------------ | ------------------------------------------------------------------------------------------ |
| `id`             | string       | Identifiant unique de la fuite                                                             |
| `title`          | string       | Nom de l'entité touchée (ex. « Free »)                                                 |
| `description`    | string       | Résumé court, nettoyé du markdown,**max 500 caractères**                         |
| `date`           | string       | Date de publication de la fuite (`YYYY-MM-DD HH:MM:SS` ou `YYYY-MM-DDTHH:MM`)          |
| `affected_count` | int          | Nombre de personnes potentiellement concernées (0 = non communiqué)                      |
| `data_volume_gb` | float\| null | Volume de données fuitées en Go, si connu                                                |
| `source`         | string       | Source de l'alerte (nom de forum, lien, etc.)                                              |
| `sector`         | string       | Secteur d'activité (ex. « Commerce », « Télécoms »)                                 |
| `data_types`     | string[]     | Types de données exposées (ex.`["Emails","Mots de passe"]`)                            |
| `url`            | string       | **URL du post de la fuite sur FrenchBreaches** (à utiliser pour le lien de l'embed) |
| `short_url`      | string       | URL courte de redirection (alternative compacte)                                           |

Champs supplémentaires **uniquement en mode `detail`** :

| Champ             | Type   | Description                                                             |
| ----------------- | ------ | ----------------------------------------------------------------------- |
| `header_image`  | string | Image d'en-tête de la fuite (URL absolue, pour le`image` de l'embed) |
| `logo`          | string | Logo de l'entité (URL absolue)                                         |
| `last_modified` | string | Date de dernière modification                                          |
| `status`        | string | Statut de la fuite (`published` par défaut)                          |

```json
{
  "id": "blf_697f831a59c3c",
  "title": "Free",
  "description": "5,1 millions de personnes",
  "date": "2024-10-25",
  "affected_count": 0,
  "data_volume_gb": null,
  "source": "https://bonjourlafuite.eu.org/img/free.png",
  "sector": "",
  "data_types": ["Adresse e-mail", "IBAN", "Nom, prénom"],
  "url": "https://frenchbreaches.com/alertes/free-blf_697f831a59c3c",
  "short_url": "https://frenchbreaches.com/r/hzOe58"
}
```

---

## 3. Réponses d'erreur

| Code HTTP | Signification                                                 |
| --------- | ------------------------------------------------------------- |
| `400`   | Paramètre manquant ou invalide (message en`error`)         |
| `405`   | Méthode autre que GET                                        |
| `429`   | Quota horaire dépassé (retourne`retry_after` en secondes) |
| `500`   | Erreur interne                                                |

```json
{ "success": false, "error": "`q` must be between 2 and 80 characters" }
{ "success": false, "error": "Too Many Requests", "retry_after": 3600 }
```

---

## 4. Commande `/alerte` — détection des nouvelles fuites

Aucun webhook nécessaire : le bot **poll** l'endpoint `dernieres` avec le paramètre `since`.

1. À la première exécution : `GET ?action=dernieres&limit=1` → stocker `data[0].date`.
2. En boucle (toutes les 2 à 5 min) : `GET ?action=dernieres&since=<date stockée>`.
3. Chaque fuite retournée est **nouvelle** → poster l'embed, puis mettre à jour la date stockée avec la dernière vue.
4. Même si plusieurs fuites arrivent entre deux polls, elles sont toutes remontées.

Exemple Python (asynchrone) :

```python
import aiohttp, asyncio

BASE = "https://frenchbreaches.com/api/bot.php"
last_seen = None  # persister cette valeur (fichier/DB)

async def poll():
    global last_seen
    async with aiohttp.ClientSession() as s:
        while True:
            params = {"action": "dernieres"}
            if last_seen:
                params["since"] = last_seen
            async with s.get(BASE, params=params) as r:
                data = (await r.json()).get("data", [])
            for leak in data:
                await post_embed(leak)      # implémentation Discord
            if data:
                last_seen = data[0]["date"] # liste triée date DESC
            await asyncio.sleep(120)

asyncio.run(poll())
```

> ⚠️ Le paramètre `since` s'exprime en **UTC**. Les dates renvoyées par l'API utilisent le fuseau du site ; comparez toujours via des timestamps normalisés.

**Alertes par secteur :** ajoutez `&sector=<secteur>` au polling pour ne recevoir que les fuites d'un domaine (ex. canal dédié au secteur public). Exemple : `GET ?action=dernieres&since=<date>&sector=secteur public`.

---

## 5. Exemple d'embed Discord

Champs utiles pour un embed : `title`, `url`, `description`, `date`, `affected_count`, `sector`, `data_types`. En mode `detail`, ajoutez `header_image` en image de l'embed.

```python
def build_embed(leak):
    return {
        "title": leak["title"],
        "url": leak["url"],
        "description": leak["description"],
        "color": 0xFF0000 if leak["affected_count"] >= 1_000_000 else 0xE67E22,
        "fields": [
            {"name": "Personnes concernées",
             "value": f"{leak['affected_count']:,}".replace(",", " ") if leak["affected_count"] else "Non communiqué", "inline": True},
            {"name": "Secteur", "value": leak["sector"] or "Inconnu", "inline": True},
            {"name": "Types de données",
             "value": ", ".join(leak["data_types"])[:1024] or "Non précisé", "inline": False},
        ],
        "footer": {"text": "FrenchBreaches — " + leak["date"]},
    }
```

## 5.1 Exemple Discord.js (v14) — commande `/fuite` + alerte par polling

```js
const { Client, GatewayIntentBits, EmbedBuilder, SlashCommandBuilder } = require("discord.js");
const BASE = "https://frenchbreaches.com/api/bot.php";

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

async function api(action, params = {}) {
  const url = new URL(BASE);
  url.searchParams.set("action", action);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  return (await fetch(url)).json();
}

function embed(leak) {
  return new EmbedBuilder()
    .setTitle(leak.title)
    .setURL(leak.url)
    .setDescription(leak.description)
    .setColor(leak.affected_count >= 1_000_000 ? 0xFF0000 : 0xE67E22)
    .addFields(
      { name: "Personnes concernées", value: leak.affected_count ? leak.affected_count.toLocaleString("fr-FR") : "Non communiqué", inline: true },
      { name: "Secteur", value: leak.sector || "Inconnu", inline: true },
      { name: "Types de données", value: (leak.data_types?.join(", ") || "Non précisé").slice(0, 1024), inline: false },
    )
    .setFooter({ text: `FrenchBreaches — ${leak.date}` });
}

client.on("ready", () => console.log("Bot prêt"));

// Commande slash /fuite <entreprise>
client.on("interactionCreate", async (i) => {
  if (!i.isChatInputCommand() || i.commandName !== "fuite") return;
  const res = await api("fuite", { q: i.options.getString("entreprise") });
  if (!res.data?.length) return i.reply({ content: "Aucune fuite trouvée.", ephemeral: true });
  await i.reply({ embeds: res.data.map(embed) });
});

// Polling /alerte : nouvelle fuite -> embed, puis appel /detail pour l'image
let lastSeen = null; // persister (fichier/DB)
setInterval(async () => {
  const params = { action: "dernieres" };
  if (lastSeen) params.since = lastSeen;
  const res = await api("dernieres", params);
  for (const leak of res.data || []) {
    const detail = (await api("detail", { id: leak.id })).data;
    const ch = await client.channels.fetch("ID_DU_CANAL");
    await ch.send({ embeds: embed(detail).setImage(detail.header_image || null) });
  }
  if (res.data?.length) lastSeen = res.data[0].date; // trié date DESC
}, 120_000);

client.login("TOKEN");
```

---

## 6. Bonnes pratiques & limites

- **Rate limit :** 300 req/h/IP. Un poll toutes les 2-5 min ≈ 30 req/h : large marge.
- **Respectez le cache** (`Cache-Control` dans les headers) ; ne contournez pas le quota.
- **Aucune donnée personnelle n'est exposée** : l'API ne fournit que les métadonnées des fuites (pas de recherche par email).
- Indiquez la source `FrenchBreaches` dans le footer des embeds.

## 7. Exemples complets (curl)

```bash
# Recherche
curl "https://frenchbreaches.com/api/bot.php?action=fuite&q=auchan"

# Recherche filtrée par secteur
curl "https://frenchbreaches.com/api/bot.php?action=fuite&q=free&sector=telecom"

# Détail complet d'une fuite (description + images)
curl "https://frenchbreaches.com/api/bot.php?action=detail&id=mt4685xhf4it99ffgkq"

# 5 dernières fuites
curl "https://frenchbreaches.com/api/bot.php?action=dernieres&limit=5"

# Nouvelles fuites depuis une date
curl "https://frenchbreaches.com/api/bot.php?action=dernieres&since=2026-08-22T09:00:00Z"

# Dernières fuites d'un secteur
curl "https://frenchbreaches.com/api/bot.php?action=dernieres&sector=telecom&limit=3"

# Statistiques globales
curl "https://frenchbreaches.com/api/bot.php?action=stats"
```

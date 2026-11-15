# Claude sur Alexa (skill privée, en français)

Une skill Alexa personnalisée qui envoie tes questions à l'API Claude d'Anthropic et lit la réponse sur tes Amazon Echo.

- « Alexa, demande à Claude pourquoi le ciel est bleu » : question directe.
- « Alexa, ouvre Claude » : conversation, plusieurs questions à la suite.
- « Alexa, demande à Claude de réfléchir à … » : réponse plus longue et structurée.

La skill est hébergée gratuitement par Amazon (Alexa-hosted, Python) et reste en mode Développement : elle ne fonctionne que sur les appareils liés à ton compte Amazon.

## Installation

### 1. Lier les crédits API de l'abonnement Claude Max

Sur **claude.ai**, dans un navigateur web : **Paramètres > Facturation**, section **API credits**, bouton **Link organization**. Crée une organisation Console dédiée, par exemple « Arnaud perso ».

- Ce lien est définitif : il ne peut être changé que par le support.
- Sans carte bancaire enregistrée sur la Console, les requêtes s'arrêtent simplement quand les crédits du mois sont épuisés. La skill dit alors « Mes crédits sont épuisés pour ce mois-ci. »

### 2. Créer une clé API

Sur **platform.claude.com**, dans cette organisation, crée une clé API réservée à la skill (nom suggéré : `alexa`). Copie-la : elle n'est affichée qu'une fois.

### 3. Publier ce dépôt sur GitHub en public

L'import Alexa ne lit que les dépôts publics. Avant de le rendre public, vérifie qu'aucune clé ne s'y trouve :

```bash
git grep -n "sk-ant-" -- . ':!README.md'
```

Les seules lignes attendues sont factices : le modèle `sk-ant-...` de `lambda/claude_secrets.example.py` et les valeurs de test du dossier `tests/`.

### 4. Créer la skill dans la console Alexa

Sur https://developer.amazon.com/alexa/console/ask, avec le compte Amazon de tes Echo :

1. **Create Skill**.
2. Nom : `Claude`. Langue : **French (FR)**.
3. Type d'expérience : **Other**. Modèle : **Custom**.
4. Hébergement : **Alexa-hosted (Python)**.
5. À l'écran des modèles, clique sur **Import skill** et colle l'URL du dépôt, terminée par `.git`.

L'import prend une à deux minutes.

### 5. Ajouter la clé API

Onglet **Code** :

1. Dans le dossier `lambda`, crée un fichier `claude_secrets.py`.
2. Mets-y une seule ligne, avec ta clé :

   ```python
   ANTHROPIC_API_KEY = "sk-ant-api03-…"
   ```

3. **Save**, puis **Deploy**.

Ce fichier n'existe que chez Amazon. Il n'est pas dans le dépôt Git, et `.gitignore` l'exclut.

### 6. Construire le modèle vocal

Onglet **Build** :

1. Dans **Invocations > Skill Invocation Name**, vérifie que le nom est `claude`.
2. Clique sur **Build Model** et attends la fin du build.

Si la console refuse un nom d'un seul mot, mets `assistant claude`, relance **Build Model**, et dis ensuite « Alexa, demande à assistant Claude … ».

### 7. Tester

Onglet **Test** : passe le sélecteur sur **Development**, puis tape ou dis :

- `demande à claude pourquoi le ciel est bleu`
- `demande à claude de réfléchir à l'avenir des voitures électriques`
- `ouvre claude`, puis `comment faire une pâte à crêpes`, puis `non merci`

### 8. Vérifier les Echo

Dans l'application Alexa, chaque Echo doit être :

- réglé en **Français (France)** (Appareils > ton Echo > Paramètres > Langue) ;
- lié au **même compte Amazon** que la console développeur.

La skill n'existe que pour la langue `fr-FR` : un Echo réglé en « Français (Canada) » ou en anglais ne la trouvera pas.

## Changer de modèle

Tous les réglages sont dans `lambda/config.py`. Après chaque modification dans l'onglet **Code** : **Save**, puis **Deploy**.

```python
MODEL_DEFAULT = "claude-sonnet-5-5"   # questions normales
MODEL_FAST    = "claude-haiku-5-5"    # repli si les réponses sont trop souvent coupées
MODEL_DEEP    = "claude-sonnet-5-5"   # « réfléchis à … »
```

Pour passer sur Haiku, plus rapide, remplace la première ligne par :

```python
MODEL_DEFAULT = "claude-haiku-5-5"
```

Fais de même pour `MODEL_DEEP` si les réponses approfondies sont coupées elles aussi. Pour revenir à Sonnet, remets `"claude-sonnet-5-5"`.

Si tu utilises un autre modèle que ces deux-là, ajoute-le aussi dans la table `THINKING_OFF` du même fichier. Elle coupe la phase de réflexion du modèle, qui consomme du temps et des tokens de sortie ; la valeur à envoyer dépend du modèle. Sans entrée dans cette table, le modèle réfléchit avant de répondre et dépassera souvent les 8 secondes.

### Juger si Sonnet tient le délai

Alexa coupe une skill qui ne répond pas en 8 secondes environ ; la skill abandonne l'appel à Claude après 6,5 secondes (`HTTP_TIMEOUT_S`). Chaque appel écrit sa durée dans les journaux : onglet **Code > CloudWatch Logs** (choisis la région Europe). Tu y verras des lignes comme :

```
Claude model=claude-sonnet-5-5 HTTP 200 en 2.41s stop=end_turn tokens_in=212 tokens_out=96
Claude model=claude-sonnet-5-5 TIMEOUT après 6.50s
```

Si les durées dépassent régulièrement 5 secondes ou si les `TIMEOUT` sont fréquents, passe sur Haiku. `stop=max_tokens` signale une réponse coupée par la limite de longueur : la skill retire alors la phrase inachevée.

## Dépannage

| Symptôme | Cause probable et solution |
|---|---|
| « Désolé, la réponse prenait trop de temps. » ou réponse coupée net | Claude a dépassé 6,5 secondes. Regarde les durées dans les journaux, puis passe `MODEL_DEFAULT` sur Haiku. |
| « La clé API n'est pas configurée. » | `lambda/claude_secrets.py` est absent, mal nommé, ou contient encore `sk-ant-...`. Corrige, **Save**, **Deploy**. |
| « La clé API est refusée. » | Clé erronée, révoquée, ou d'une autre organisation. Crée-en une nouvelle sur platform.claude.com. |
| « Mes crédits sont épuisés pour ce mois-ci. » | Les crédits mensuels du plan Max sont consommés. Ils reviennent au renouvellement. |
| « Je reçois trop de demandes à la fois. » ou « Le service Claude est surchargé. » | Limite de débit ou surcharge passagère côté Anthropic. Réessaie plus tard. |
| « Ma demande a été refusée par le service Claude. » | L'API a rejeté la requête (modèle inconnu, réglage invalide). Le message exact est dans les journaux. |
| Alexa répond qu'elle ne trouve pas la skill | Echo dans une autre langue que Français (France), autre compte Amazon, ou test non passé sur **Development** (étape 7). |
| Alexa comprend « Claude » de travers ou lance autre chose | Change le nom d'invocation en `assistant claude` (étape 6) et relance **Build Model**. |
| « Je n'ai pas compris. » | La phrase ne commence par aucune tournure connue. Commence par pourquoi, comment, explique-moi, dis-moi, etc. |
| Pas de « Je réfléchis… » avant la réponse | Sans gravité : l'annonce d'attente a échoué, la raison est dans les journaux. La réponse arrive quand même. |

## Coûts

- **Amazon : 0 €.** L'hébergement Alexa-hosted est gratuit dans les limites de l'offre AWS incluse, très au-dessus d'un usage domestique, et la skill n'est pas publiée.
- **Anthropic :** couvert par les crédits API mensuels de l'abonnement Claude Max. Sans carte sur la Console, aucun dépassement n'est facturé.

## Comment ça marche

```
skill-package/
  skill.json                          manifeste, locale fr-FR seule
  interactionModels/custom/fr-FR.json modèle vocal
lambda/
  lambda_function.py                  handlers Alexa
  config.py                           modèles, délais, prompts, phrases prononcées
  claude_client.py                    appel HTTP à l'API Claude
  text_utils.py                       nettoyage du markdown, échappement SSML
  claude_secrets.example.py           modèle du fichier de clé
tests/                                tests pytest et requêtes Alexa d'exemple
```

Ce format (`lambda/` et `skill-package/` à la racine) est l'un des deux que l'import Alexa-hosted accepte, d'après la [documentation Amazon](https://developer.amazon.com/en-US/docs/alexa/hosted-skills/alexa-hosted-skills-git-import.html). Le dossier `tests/` ne sert qu'au développement : la skill ne l'utilise pas.

Pendant l'appel à Claude, Alexa dit « Je réfléchis… ». La skill garde en mémoire les cinq derniers échanges de la session, ce qui permet d'enchaîner avec « et au coucher du soleil ? ». Après chaque réponse, elle attend la suite ; « non merci », « c'est tout » ou « stop » ferment la session.

### Trois choix qui s'écartent du cahier des charges

**Un intent par tournure de question.** Alexa ne transmet à la skill que le contenu du slot, sans la phrase qui l'introduit : pour « pourquoi le ciel est bleu », la skill reçoit seulement « le ciel est bleu ». Avec un seul `QuestionIntent`, Claude ne saurait pas si tu as dit pourquoi, quand ou où. Chaque tournure a donc son propre intent (`QuestionPourquoiIntent`, `QuestionCommentIntent`, etc.), et la table `QUESTION_PREFIXES` de `config.py` remet le bon début de phrase. Pour ajouter une tournure, ajoute un intent dans `fr-FR.json` et une ligne dans cette table ; un test vérifie que les deux restent synchronisés.

**`claude_secrets.py` au lieu de `secrets.py`.** `secrets` est le nom d'un module standard de Python. Un fichier `lambda/secrets.py` le masquerait pour toutes les bibliothèques chargées par la skill.

**Réflexion du modèle coupée.** Les modèles Claude actuels réfléchissent avant de répondre, et cette réflexion compte dans les 300 tokens de sortie et dans les 8 secondes. La skill la désactive et demande un effort `low`. Le mode « réfléchis à … » change donc la longueur et la structure de la réponse, pas la profondeur de raisonnement du modèle.

## Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Les tests n'appellent jamais la vraie API : les réponses de Claude sont simulées.

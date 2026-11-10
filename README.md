# Druk Kha

English in, Bhutanese Dzongkha out. Open this folder in VS Code.

## Run it

You need Node.js 22 or newer.

1. Open a terminal in this folder.
2. Install dependencies:

```bash
npm install
```

3. Create a file named `.env` in this folder (same place as `package.json`) with your xAI key:

```bash
XAI_API_KEY=your_key_here
```

Get a key from [console.x.ai](https://console.x.ai). Replies will not work without it. Do not commit this file.

4. Start the app:

```bash
npm run dev
```

5. Open [http://localhost:8080](http://localhost:8080).

Type in English. The reply is Bhutanese Dzongkha, with pronunciation and an English meaning. "Thank you" answers with རྗེམ་པ་ལེགས་སོ། (Jembalaekso).

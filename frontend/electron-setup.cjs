// Writes a package.json into dist-electron/electron/ so Node/Electron treats
// the compiled CommonJS files as CJS even though the root package.json has "type": "module".
const fs = require('fs')
const path = require('path')
const dir = path.join(__dirname, 'dist-electron', 'electron')
fs.mkdirSync(dir, { recursive: true })
fs.writeFileSync(path.join(dir, 'package.json'), JSON.stringify({ type: 'commonjs' }))

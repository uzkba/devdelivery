// cleanup-stray-js.mjs
import { readdirSync, statSync, unlinkSync } from "fs";
import { join, extname, basename } from "path";

const SRC_DIR = "./src";
let removed = 0;

function walk(dir) {
    const entries = readdirSync(dir);
    for (const entry of entries) {
        const full = join(dir, entry);
            if (statSync(full).isDirectory()) {
                if (entry === "node_modules") continue;
                walk(full);
                continue;
            }
            if (extname(entry) !== ".js") continue;

            const name = basename(entry, ".js");
            const hasTs = entries.some(
                (f) => f === `${name}.ts` || f === `${name}.tsx`,
            );

            if (hasTs) {
                unlinkSync(full);
                console.log("removido:", full);
                removed++;
            }
    }
}

walk(SRC_DIR);
console.log(`\nTotal removido: ${removed}`);
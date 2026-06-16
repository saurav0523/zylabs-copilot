import { remark } from 'remark';
import html from 'remark-html';
import gfm from 'remark-gfm';

const text = `Business Pain           1. Manual RFP analysis
Points                  consumes excessive
(high-impact)           hours -> slow bid cycles.

| Col 1 | Col 2 |
| Data 1 | Data 2 |

| No Header | Data |
| Row 2 | Data 2 |`;

remark()
  .use(gfm)
  .use(html)
  .process(text)
  .then((file) => console.log(String(file)));

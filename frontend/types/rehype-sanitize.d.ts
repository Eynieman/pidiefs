declare module "rehype-sanitize" {
  import type { Plugin } from "unified";
  interface Schema {
    tagNames?: string[];
    attributes?: Record<string, (string | RegExp)[]>;
    strip?: string[];
    allowComments?: boolean;
    allowDoctypes?: boolean;
  }
  const rehypeSanitize: Plugin<[Schema?]>;
  export default rehypeSanitize;
  export { Schema };
}

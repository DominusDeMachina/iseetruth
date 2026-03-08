import createClient from "openapi-fetch";
import type { paths } from "./api-types.generated";

export const api = createClient<paths>({
  baseUrl: "",
});

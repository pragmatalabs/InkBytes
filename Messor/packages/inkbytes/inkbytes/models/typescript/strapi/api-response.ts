import { OutletSource } from "../outlet/outlet-source";
import { Meta } from "./meta";


export interface ApiResponse {
  data: OutletSource[];
  meta: Meta;
}

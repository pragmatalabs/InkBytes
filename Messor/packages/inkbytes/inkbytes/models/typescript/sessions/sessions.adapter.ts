
import { Session } from "./session";

export class SessionsAdapter {
    adapt=(item: Session): Session=>{
        const attributes = item.attributes;
        // You can add any transformation or default value setting logic here
        return new Session(item.id, attributes);
    }
}

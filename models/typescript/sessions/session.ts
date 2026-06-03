import { SessionAttributes } from "./session-attributes";

export class Session {
    id: number;
    attributes: SessionAttributes;

    constructor(id: number, attributes: SessionAttributes) {
        this.id = id;
        this.attributes = attributes;
    }
}



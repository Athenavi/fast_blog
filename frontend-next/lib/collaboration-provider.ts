import * as Y from 'yjs';
import {WebsocketProvider} from 'y-websocket';

/**
 * 自定义WebSocket提供者
 * 桥接y-websocket协议到FastBlog的后端API
 */
export class FastBlogWebsocketProvider extends WebsocketProvider {
    constructor(
        serverUrl: string,
        roomName: string,
        doc: Y.Doc,
        options: any = {}
    ) {
        // 调用父类构造函数
        super(serverUrl, roomName, doc, options);

        console.log('[FastBlogProvider] Initialized for room:', roomName);
    }
}

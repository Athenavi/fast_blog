import {useEffect, useRef, useState, useCallback} from 'react';
import * as Y from 'yjs';
import {getConfig} from '@/lib/config';

export interface Collaborator {
  client_id: string;
  user_id?: number | string;
  user_name?: string;
  color?: string;
}

export interface YjsCollabState {
  ydoc: Y.Doc;
  connected: boolean;
  connecting: boolean;
  collaborators: Collaborator[];
  error?: string;
  start: () => void;
  stop: () => void;
  sendHtmlSnapshot: (html: string) => void;
  requestSave: () => void;
}

const COLLABORATOR_COLORS = [
  '#ff6b6b', '#51cf66', '#339af0', '#f59f00', '#cc5de8',
  '#20c997', '#e64980', '#15aabf', '#fab005', '#7950f2',
];

export function useYjsCollaboration(
  documentId: string | null,
  articleId?: number | string | null,
  token?: string | null,
): YjsCollabState {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [error, setError] = useState<string | undefined>();

  const ydocRef = useRef<Y.Doc>(new Y.Doc());
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const pingTimerRef = useRef<ReturnType<typeof setInterval>>();
  const colorIndexRef = useRef(0);
  const myClientIdRef = useRef<string>('');
  const stoppedRef = useRef(false);

  const sendJson = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const sendHtmlSnapshot = useCallback((html: string) => {
    sendJson({type: 'html_snapshot', html});
  }, [sendJson]);

  const requestSave = useCallback(() => {
    sendJson({type: 'save'});
  }, [sendJson]);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    if (pingTimerRef.current) clearInterval(pingTimerRef.current);
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    setConnecting(false);
    setCollaborators([]);
  }, []);

  const start = useCallback(() => {
    if (!documentId) return;
    stoppedRef.current = false;
    setConnecting(true);
    setError(undefined);

    // Use API_BASE_URL from config (backend URL), same as REST API client
    const baseUrl = getConfig().API_BASE_URL || `http://${window.location.host}`;
    const wsBase = baseUrl.replace(/^https?:/, (m) => m === 'https:' ? 'wss:' : 'ws:');
    const wsUrl = `${wsBase}/api/v2/collaboration/yjs/ws/${documentId}?article_id=${articleId || ''}${token ? `&token=${encodeURIComponent(token)}` : ''}`;
    console.debug('[Yjs WS] Connecting to:', wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    const doc = ydocRef.current;

    ws.onopen = () => {
      if (stoppedRef.current) { ws.close(); return; }
      setConnected(true);
      setConnecting(false);
      setError(undefined);

      // Start ping interval
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({type: 'ping'}));
        }
      }, 15000);
    };

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        // Binary Yjs update
        event.data.arrayBuffer().then(buf => {
          const update = new Uint8Array(buf);
          Y.applyUpdate(doc, update);
        });
        return;
      }

      // JSON message
      try {
        const msg = JSON.parse(event.data);
        const type = msg.type;

        if (type === 'welcome') {
          myClientIdRef.current = msg.client_id || '';
          // Load HTML snapshot into doc if present
          if (msg.html_snapshot) {
            // The html_snapshot from backend is plain HTML, Yjs handles it via y-prosemirror
            // We emit a custom event for the consumer to handle
            window.dispatchEvent(new CustomEvent('yjs-welcome-html', {
              detail: { html: msg.html_snapshot, documentId },
            }));
          }
          // Set initial collaborators
          const existing: Collaborator[] = (msg.clients || []).map((c: any) => ({
            client_id: c.client_id,
          }));
          setCollaborators(existing);
        } else if (type === 'awareness') {
          const state = msg.state || {};
          if (state.type === 'user_joined') {
            setCollaborators(prev => {
              if (prev.find(c => c.client_id === state.client_id)) return prev;
              const color = COLLABORATOR_COLORS[colorIndexRef.current % COLLABORATOR_COLORS.length];
              colorIndexRef.current++;
              return [...prev, {
                client_id: state.client_id,
                user_id: state.user_id,
                user_name: state.user_name,
                color,
              }];
            });
          } else if (state.type === 'user_left') {
            setCollaborators(prev => prev.filter(c => c.client_id !== state.client_id));
          } else if (state.client_id && state.client_id !== myClientIdRef.current) {
            // Cursor awareness update
            setCollaborators(prev => {
              const idx = prev.findIndex(c => c.client_id === state.client_id);
              if (idx === -1) return prev;
              const updated = [...prev];
              updated[idx] = {...updated[idx], ...state};
              return updated;
            });
          }
        } else if (type === 'save_result') {
          window.dispatchEvent(new CustomEvent('yjs-save-result', {
            detail: { success: msg.success, message: msg.message },
          }));
        }
      } catch (e) {
        // ignore
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (!stoppedRef.current) {
        // Auto reconnect after 3s
        reconnectTimerRef.current = setTimeout(() => {
          if (!stoppedRef.current) start();
        }, 3000);
      }
    };

    ws.onerror = () => {
      setError('连接失败');
      setConnecting(false);
    };

    // Listen for Yjs doc updates and send to server
    const updateHandler = (update: Uint8Array, origin: any) => {
      if (origin === 'remote') return; // Ignore remote updates
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(update);
      }
    };
    doc.on('update', updateHandler);

    // Store cleanup reference
    (ws as any).__yjsCleanup = () => {
      doc.off('update', updateHandler);
    };
  }, [documentId, articleId, token]);

  // Cleanup on unmount
  useEffect(() => {
    return () => { stop(); };
  }, [stop]);

  // Broadcast awareness (cursor/selection)
  const broadcastAwareness = useCallback((awareState: Record<string, any>) => {
    sendJson({type: 'awareness', state: awareState});
  }, [sendJson]);

  return {
    ydoc: ydocRef.current,
    connected,
    connecting,
    collaborators,
    error,
    start,
    stop,
    sendHtmlSnapshot,
    requestSave,
  };
}

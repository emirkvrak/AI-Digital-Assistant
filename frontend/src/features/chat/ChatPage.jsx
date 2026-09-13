import { useTranslation } from "react-i18next";
import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { Chat } from "./Chat";
import { Controls } from "./Controls";
import { RightSidebar } from "../../components/Sidebar/RightSidebar";
import { Sidebar as LeftSidebar } from "../../components/Sidebar/Sidebar";

import instance from "../../api/axiosInstance";
import styles from "./ChatPage.module.css";

import { SettingsIcon, UserIcon } from "../../components/Icons";
import { LanguageSwitcher } from "../../components/LanguageSwitcher/LanguageSwitcher";
import { useUserStore } from "../../store/useUserStore";
import { toast } from "react-toastify";
import { getPendingResources } from "../../utils/storage";

function ChatPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const userEmail = useUserStore((state) => state.userEmail);
  const setUserEmail = useUserStore((state) => state.setUserEmail);
  const setIsAuthenticated = useUserStore((state) => state.setIsAuthenticated);

  const [messages, setMessages] = useState([]);
  const [chatRooms, setChatRooms] = useState([]);
  const [aktifChatRoomId, setAktifChatRoomId] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isAiTyping, setIsAiTyping] = useState(false);
  const pollingRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (aktifChatRoomId && chatRooms.length > 0) {
      const selectedRoom = chatRooms.find(
        (room) => room._id === aktifChatRoomId
      );

      const pendingList = getPendingResources();

      const formattedFiles = (selectedRoom?.uploaded_files || []).map(
        (file) => ({
          filename: file.filename,
          displayName: file.original_name || file.title || file.source,
          original_name: file.original_name || file.title || file.source,
          raw_text: file.raw_text || "",
          isPending: pendingList.includes(file.filename),
        })
      );

      setUploadedFiles(formattedFiles);
    }
  }, [aktifChatRoomId, chatRooms]);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await instance.get("/auth/me");
        if (response.data.success) {
          setUserEmail(response.data.data.email);
        } else {
          setUserEmail("");
          setIsAuthenticated(false);
          navigate("/signin");
        }
      } catch (error) {
        console.error("Kullanıcı bilgisi alınamadı:", error);
        setUserEmail("");
        setIsAuthenticated(false);
        navigate("/signin");
      }
    };

    const fetchChatRooms = async () => {
      try {
        const res = await instance.get("/chat/fetch-chat-rooms");
        if (res.data.success) {
          const rooms = res.data.data.chat_rooms;

          const sortedRooms = rooms.sort(
            (a, b) => new Date(b.created_at) - new Date(a.created_at)
          );

          setChatRooms(sortedRooms);

          if (sortedRooms.length > 0) {
            const latestRoomId = sortedRooms[0]._id;
            setAktifChatRoomId(latestRoomId);
            fetchMessagesForRoom(latestRoomId);
          }
        }
      } catch (error) {
        console.error("Chat odaları alınamadı:", error);
      }
    };

    const load = async () => {
      try {
        await Promise.all([fetchUserData(), fetchChatRooms()]);
      } catch (e) {
        console.error("Veriler alınırken hata:", e);
      }
    };

    load();
  }, [navigate, setIsAuthenticated, setUserEmail]);

  async function fetchMessagesForRoom(roomId) {
    try {
      const res = await instance.get(`/chat/fetch-messages?room_id=${roomId}`);
      if (res.data.success) {
        setMessages(res.data.data.messages || []);
      } else {
        setMessages([]);
      }
    } catch (error) {
      console.error("Chat odası mesajları alınamadı:", error);
      setMessages([]);
    }
  }

  const handleContentSend = useCallback(
    async (content, selected_files) => {
      let currentRoomId = aktifChatRoomId;
      setIsAiTyping(true);

      try {
        if (!currentRoomId) {
          const newChatRes = await instance.post("/chat/new-chat", {
            room_name: `Sohbet ${chatRooms.length + 1}`,
          });

          if (newChatRes.data.success) {
            const { room_id, room_name, created_at } = newChatRes.data.data;
            currentRoomId = room_id;

            setChatRooms((prev) => [
              { _id: room_id, room_name, created_at },
              ...prev,
            ]);
            setAktifChatRoomId(room_id);
            setMessages([]);
          } else {
            toast.error(t("chat_creation_failed"));
            return;
          }
        }

        const res = await instance.post("/chat/send-message", {
          room_id: currentRoomId,
          content: content,
          selected_files: selected_files,
        });

        if (res.data.success) {
          const newMessage = {
            content,
            role: "user",
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, newMessage]);

          const pollingStartedAt = Date.now();
          const interval = setInterval(async () => {
            if (Date.now() - pollingStartedAt >= 30000) {
              clearInterval(interval);
              pollingRef.current = null;
              setIsAiTyping(false);
              toast.error(t("message_send_failed"));
              return;
            }

            try {
              const response = await instance.get(
                `/chat/fetch-messages?room_id=${currentRoomId}`
              );
              if (response.data.success) {
                const allMessages = response.data.data.messages;
                const lastMessage = allMessages[allMessages.length - 1];

                if (lastMessage && lastMessage.role === "assistant") {
                  setMessages((prev) => {
                    const exists = prev.some(
                      (msg) => msg._id === lastMessage._id
                    );
                    return exists ? prev : [...prev, lastMessage];
                  });
                  setIsAiTyping(false);
                  clearInterval(interval);
                  pollingRef.current = null;
                }
              }
            } catch (err) {
              console.error("AI cevabı kontrol edilirken hata:", err);
              clearInterval(interval);
              pollingRef.current = null;
              setIsAiTyping(false);
              toast.error("AI cevabı alınamadı (hata oluştu).");
            }
          }, 1000);
          pollingRef.current = interval;
        } else {
          toast.error(t("message_send_failed"));
          setIsAiTyping(false);
        }
      } catch (error) {
        console.error("Mesaj gönderilemedi:", error);
        toast.error(t("message_send_failed"));
        setIsAiTyping(false);
      }
    },
    [
      aktifChatRoomId,
      chatRooms,
      t,
      setMessages,
      setChatRooms,
      setAktifChatRoomId,
    ]
  );

  const handleNewChat = useCallback(async () => {
    const validFiles = uploadedFiles.filter(
      (f) => f.raw_text && f.raw_text.trim()
    );

    if (chatRooms.length === 0 && validFiles.length === 0) {
      toast.warn(t("empty_chat_warning"));
      return;
    }

    if (validFiles.length === 0) {
      toast.warn(t("empty_chat_warning"));
      return;
    }

    try {
      const newRoomName = t("new_chat");
      const res = await instance.post("/chat/new-chat", {
        room_name: newRoomName,
      });

      if (res.data.success) {
        const { room_id, room_name, created_at } = res.data.data;

        setChatRooms((prev) => [
          { _id: room_id, room_name, created_at, messages: [] },
          ...prev,
        ]);

        setAktifChatRoomId(room_id);
        setMessages([]);
      } else {
        toast.error(t("new_chat_failed"));
      }
    } catch (error) {
      console.error("Yeni chat oluşturulamadı:", error);
      toast.error(t("new_chat_failed"));
    }
  }, [chatRooms, uploadedFiles, t]);

  const handleSelectChatRoom = useCallback(
    async (roomId) => {
      try {
        setAktifChatRoomId(roomId);
        localStorage.setItem("active_chat_room_id", roomId);

        const res = await instance.get(
          `/chat/fetch-messages?room_id=${roomId}`
        );
        if (res.data.success) {
          setMessages(res.data.data.messages || []);
        } else {
          toast.error(t("fetch_messages_failed"));
          setMessages([]);
        }

        const updatedRoomRes = await instance.get("/chat/fetch-chat-rooms");
        if (!updatedRoomRes.data.success) {
          toast.error(t("fetch_chat_room_failed"));
          return;
        }

        const updatedRooms = updatedRoomRes.data.data.chat_rooms;
        setChatRooms(updatedRooms);

        const selectedRoom = updatedRooms.find((room) => room._id === roomId);
        const pendingList = getPendingResources();

        const uploaded = (selectedRoom?.uploaded_files || []).map((file) => ({
          filename: file.filename,
          displayName:
            file.original_name || file.title || file.source || "Unnamed",
          original_name:
            file.original_name || file.title || file.source || "Unnamed",
          raw_text: file.raw_text || "",
          isPending: pendingList.includes(file.filename),
        }));

        setUploadedFiles(uploaded);
      } catch (error) {
        console.error("Chat odası alınamadı:", error);
        toast.error(t("fetch_chat_room_failed"));
        setMessages([]);
        setUploadedFiles([]);
      }
    },
    [t]
  );

  const handleSignOut = useCallback(async () => {
    try {
      await instance.post("/auth/logout");
      toast.success(t("logout_successful"));
    } catch {
      toast.error(t("logout_failed"));
    } finally {
      setUserEmail("");
      setIsAuthenticated(false);
      setIsProfileMenuOpen(false);
      navigate("/signin");
    }
  }, [navigate, t, setUserEmail, setIsAuthenticated]);

  return (
    <div className={styles.App}>
      <LeftSidebar
        chatRooms={chatRooms}
        toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        isSidebarOpen={isSidebarOpen}
        onNewChat={handleNewChat}
        onSelectChatRoom={handleSelectChatRoom}
        setChatRooms={setChatRooms}
        aktifChatRoomId={aktifChatRoomId}
        setAktifChatRoomId={setAktifChatRoomId}
        setMessages={setMessages}
        setUploadedFiles={setUploadedFiles}
        uploadedFiles={uploadedFiles}
      />
      <div className={styles.MainContent}>
        <header className={styles.Header}>
          <img className={styles.Logo} src="/assistant.png" />

          {userEmail && (
            <p style={{ fontSize: "14px", color: "#ccc", marginLeft: "10px" }}>
              {t("welcome_message", { email: userEmail })}
            </p>
          )}

          <div className={styles.HeaderIcons}>
            <LanguageSwitcher />

            <div className={styles.ProfileContainer}>
              <button
                className={styles.ProfileButton}
                onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              >
                <UserIcon size={24} fill="#e3e3e3" />
              </button>
              {isProfileMenuOpen && (
                <div className={styles.ProfileMenu}>
                  <button
                    className={styles.SignOutButton}
                    onClick={handleSignOut}
                  >
                    {t("sign_out")}
                  </button>
                  <button
                    className={styles.SignOutButton}
                    onClick={() => navigate("/profile")}
                  >
                    {t("profile")}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        <div className={styles.ChatContainer}>
          <Chat messages={messages} isAiTyping={isAiTyping} />
        </div>
        <Controls
          onSend={handleContentSend}
          isAiTyping={isAiTyping}
          aktifChatRoomId={aktifChatRoomId}
          uploadedFiles={uploadedFiles}
        />
      </div>
      <RightSidebar
        isRightSidebarOpen={isRightSidebarOpen}
        toggleRightSidebar={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
        aktifChatRoomId={aktifChatRoomId}
        setAktifChatRoomId={setAktifChatRoomId}
        chatRooms={chatRooms}
        setChatRooms={setChatRooms}
        uploadedFiles={uploadedFiles}
        setUploadedFiles={setUploadedFiles}
        onAutoSummarize={handleContentSend}
        isAiTyping={isAiTyping}
      />
    </div>
  );
}

export default ChatPage;

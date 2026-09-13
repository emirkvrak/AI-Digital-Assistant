import { create } from 'zustand';

export const useUserStore = create((set) => ({
  userEmail: "",
  isAuthenticated: false,
  aktifChatRoomId: null,
  isUploading: false,

  setUserEmail: (email) => set({ userEmail: email }),
  setIsAuthenticated: (status) => set({ isAuthenticated: status }),
  setAktifChatRoomId: (id) => set({ aktifChatRoomId: id }),
  setIsUploading: (value) => set({ isUploading: value }),
}));

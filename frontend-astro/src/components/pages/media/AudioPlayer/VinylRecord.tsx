import React from 'react';
import {motion} from 'framer-motion';
import {Music} from 'lucide-react';

interface VinylRecordProps {
  coverImage: string | null;
  loadingMetadata: boolean;
  isPlaying: boolean;
  onMinimize?: () => void;
}

const VinylRecord: React.FC<VinylRecordProps> = ({coverImage, loadingMetadata, isPlaying, onMinimize}) => {
  return (
    <div className="hidden lg:flex w-[45%] items-center justify-center relative overflow-hidden">
      {/* Background glow */}
      <motion.div
        className="absolute inset-0"
        animate={{opacity: isPlaying ? 0.3 : 0.06}}
        transition={{duration: 1}}
      >
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] aspect-square rounded-full blur-3xl"
          style={{background: 'radial-gradient(circle, rgba(147,51,234,0.5), rgba(236,72,153,0.2), transparent)'}}
          animate={isPlaying ? {
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.6, 0.3],
          } : {scale: 1, opacity: 0.2}}
          transition={isPlaying ? {
            duration: 4,
            repeat: Infinity,
            ease: 'easeInOut',
          } : {duration: 0.6}}
        />
      </motion.div>

      {/* Vinyl + Tone arm container — 点击唱片可最小化 */}
      <div className="relative cursor-pointer" onClick={onMinimize}>
        {/* 唱臂 */}
        <motion.div
          className="absolute -top-8 -right-8 z-10"
          style={{transformOrigin: '16px 100%'}}
          animate={{rotate: isPlaying ? 18 : -35}}
          transition={{type: 'spring', stiffness: 90, damping: 14}}
        >
          <svg width="110" height="48" viewBox="0 0 110 48" fill="none">
            <rect x="16" y="10" width="94" height="4" rx="2" fill="url(#armGrad2)" />
            <circle cx="16" cy="12" r="10" fill="#555" stroke="#333" strokeWidth="1.5" />
            <circle cx="16" cy="12" r="4" fill="#222" />
            <circle cx="16" cy="12" r="1.5" fill="#888" />
            <rect x="92" y="2" width="18" height="20" rx="3" fill="#555" />
            <circle cx="101" cy="12" r="3" fill="#777" />
            <defs>
              <linearGradient id="armGrad2" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#999" />
                <stop offset="50%" stopColor="#666" />
                <stop offset="100%" stopColor="#444" />
              </linearGradient>
            </defs>
          </svg>
        </motion.div>

        {/* 黑胶唱片 */}
        <motion.div
          className="w-72 h-72 xl:w-80 xl:h-80 rounded-full bg-gradient-to-br from-gray-800 via-gray-900 to-black shadow-2xl flex items-center justify-center relative"
          style={{
            boxShadow: isPlaying
              ? '0 0 100px rgba(147, 51, 234, 0.35), inset 0 0 80px rgba(0,0,0,0.6)'
              : '0 0 50px rgba(147, 51, 234, 0.1), inset 0 0 80px rgba(0,0,0,0.6)',
          }}
          animate={{rotate: isPlaying ? 360 : 0}}
          transition={isPlaying
            ? {duration: 8, ease: 'linear', repeat: Infinity}
            : {duration: 0.6, ease: 'easeOut'}
          }
        >
          {/* 纹路 */}
          {[5, 10, 15, 20, 25, 30, 35].map(i => (
            <div key={i}
                 className="absolute rounded-full border border-gray-700/20"
                 style={{inset: `${i * 4}px`}}
            />
          ))}

          {/* 反光 */}
          <div className="absolute inset-2 rounded-full bg-gradient-to-br from-white/[0.06] via-transparent to-transparent pointer-events-none" />

          {/* 中心标签 */}
          <div className="w-28 h-28 xl:w-32 xl:h-32 rounded-full overflow-hidden shadow-lg relative z-10 ring-2 ring-white/10">
            {coverImage ? (
              <img
                src={coverImage}
                alt="cover"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
                {loadingMetadata ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"/>
                ) : (
                  <Music className="w-7 h-7 text-white/80"/>
                )}
              </div>
            )}
          </div>

          {/* 中心孔 */}
          <div className="absolute w-3 h-3 bg-black rounded-full z-20 border border-gray-700/50" />
        </motion.div>
      </div>
    </div>
  );
};

export default VinylRecord;
